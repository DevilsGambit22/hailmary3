from pathlib import Path
import json
import time
from datetime import datetime, timezone

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config/config.yml").read_text(encoding="utf-8"))
SLUG = CFG["club"]["slug"]

OUT = ROOT / "generated"
OUT.mkdir(exist_ok=True)

# Chess.com recommends a descriptive User-Agent. Using the public Chess.com
# username gives them a contact identity without exposing private credentials.
HEADERS = {
    "User-Agent": "ACFA-Dashboard/3.4 (Chess.com user: DevilsGambit22)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def api(url, attempts=4):
    """Serial PubAPI request with 429/5xx backoff."""
    last = None
    for attempt in range(attempts):
        try:
            r = SESSION.get(url, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 4 * (attempt + 1)))
                print(f"429 rate limit: waiting {wait}s for {url}")
                time.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                wait = 3 * (attempt + 1)
                print(f"{r.status_code}: waiting {wait}s for {url}")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"PubAPI request failed: {url}: {last}")

def normalize_member(item):
    # Chess.com club-members has historically returned dictionaries containing
    # username/joined. This also tolerates the older username-only shape.
    if isinstance(item, str):
        return {"username": item, "joined": 0}
    if isinstance(item, dict):
        return {
            "username": item.get("username", ""),
            "joined": int(item.get("joined") or 0),
        }
    return {"username": "", "joined": 0}

def best_rating(stats):
    ratings = []
    for key in ("chess_rapid", "chess_blitz", "chess_bullet", "chess_daily"):
        try:
            ratings.append(int(stats[key]["last"]["rating"]))
        except Exception:
            pass
    return max(ratings) if ratings else 0

def enrich(username, joined=0):
    profile = {}
    stats = {}
    profile_error = None
    stats_error = None

    try:
        profile = api(f"https://api.chess.com/pub/player/{username}")
    except Exception as exc:
        profile_error = str(exc)

    # Keep calls serial and friendly to the API.
    time.sleep(0.35)

    try:
        stats = api(f"https://api.chess.com/pub/player/{username}/stats")
    except Exception as exc:
        stats_error = str(exc)

    time.sleep(0.35)

    return {
        "username": username,
        "joined": joined,
        "avatar": profile.get("avatar"),
        "title": profile.get("title"),
        "rating": best_rating(stats),
        "profile_error": profile_error,
        "stats_error": stats_error,
    }

status = {
    "ok": False,
    "started_at": utc_now(),
    "finished_at": None,
    "club_endpoint": None,
    "members_endpoint": None,
    "errors": [],
}

try:
    club = api(f"https://api.chess.com/pub/club/{SLUG}")
    status["club_endpoint"] = "ok"
except Exception as exc:
    club = {}
    status["club_endpoint"] = "error"
    status["errors"].append(str(exc))

try:
    members_doc = api(f"https://api.chess.com/pub/club/{SLUG}/members")
    status["members_endpoint"] = "ok"
except Exception as exc:
    members_doc = {"weekly": [], "monthly": [], "all_time": []}
    status["members_endpoint"] = "error"
    status["errors"].append(str(exc))

raw = []
for bucket in ("weekly", "monthly", "all_time"):
    for item in members_doc.get(bucket, []) or []:
        m = normalize_member(item)
        if m["username"]:
            raw.append(m)

# Deduplicate by username, retaining the newest join timestamp if duplicates exist.
by_user = {}
for m in raw:
    key = m["username"].lower()
    old = by_user.get(key)
    if old is None or m["joined"] > old["joined"]:
        by_user[key] = m

members = list(by_user.values())
members.sort(key=lambda m: m["joined"], reverse=True)

new_limit = int(CFG.get("boards", {}).get("newest_members", {}).get("limit", 5))
newest = []
for m in members[:new_limit]:
    try:
        newest.append(enrich(m["username"], m["joined"]))
    except Exception as exc:
        status["errors"].append(f"{m['username']}: {exc}")

# Don't scan every club member for a title. Query the configured known titled
# usernames only. This avoids dozens/hundreds of PubAPI requests and 429s.
t_cfg = CFG.get("boards", {}).get("titled_players", {})
pinned = t_cfg.get("pinned_usernames", []) or []
t_limit = int(t_cfg.get("limit", 2))
titled = []
for username in pinned[:t_limit]:
    try:
        p = enrich(username)
        titled.append(p)
    except Exception as exc:
        status["errors"].append(f"{username}: {exc}")

# Preserve previous generated data if a temporary endpoint failure produced
# no useful replacement.
def keep_previous_if_empty(filename, value):
    path = OUT / filename
    if value:
        return value
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous:
                return previous
        except Exception:
            pass
    return value

newest = keep_previous_if_empty("members.json", newest)
titled = keep_previous_if_empty("titled.json", titled)

member_count = club.get("members_count")
if not isinstance(member_count, int):
    member_count = len(members)

save("members.json", newest)
save("titled.json", titled)
save("stats.json", {
    "member_count": member_count,
    "titled_count": len(titled),
    "updated_at": utc_now(),
})
save("config.json", CFG)

status["ok"] = bool(status["club_endpoint"] == "ok" and status["members_endpoint"] == "ok")
status["finished_at"] = utc_now()
save("api-status.json", status)

print(json.dumps(status, indent=2))
print(f"ACFA sync: {member_count} club members; {len(newest)} newest displayed; {len(titled)} titled displayed.")
