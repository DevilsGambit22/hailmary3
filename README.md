# ACFA Dashboard V3.2

This is the corrected build: the **actual visible dashboard and the automation system are now in the same GitHub project**.

## What is already wired together

- ACFA visual dashboard in `index.html`
- Uploaded ACFA artwork
- Newest Members board
- Titled Players board
- member count
- titled-player count
- avatars and ratings
- staff board
- announcement system
- tournament countdown
- champions podium
- GitHub scheduled Chess.com PubAPI updater
- GitHub Pages deployment workflow
- `config.yml`
- generated JSON
- `sw.js`
- `manifest.json`
- `logo.svg`
- `robots.txt`

## Publish

1. Create/open the GitHub repo for this sidebar.
2. Upload **everything inside this ZIP** to the repository root.
3. Make sure your branch is `main`.
4. Go to **Settings → Pages**.
5. Choose **GitHub Actions** as the Pages source.
6. Go to **Actions → Update ACFA Data → Run workflow**.
7. After that first run finishes, the dashboard's member/titled boards populate from public Chess.com data.
8. The workflow automatically refreshes every 6 hours.

## Normal editing

You no longer need to edit `index.html` for routine ACFA changes:

- `config/config.yml` — dashboard configuration
- `data/staff.json` — staff
- `data/announcements.json` — announcements
- `data/tournaments.json` — tournament dates
- `data/champions.json` — podium winners

The `generated/` directory is maintained by the GitHub Action.


## V3.3 changes
- All four supplied ACFA artwork files are now PNG assets with transparent edge backgrounds.
- The old JPG copies were removed.
- Added a live digital clock and date that use each visitor's browser/device local time.
- The clock updates in-browser; no API or server time is required.
- Service-worker cache bumped to V3.3 and updated for the PNG filenames.


## V3.4 PubAPI fix

The previous updater could make far too many player-profile requests while trying to discover titled players. That could trigger Chess.com rate limiting and leave the generated dashboard data empty.

V3.4 fixes that by:
- using a descriptive Chess.com PubAPI `User-Agent`;
- making requests serially with retry/backoff for 429 and 5xx responses;
- querying only the five newest members;
- querying only configured titled usernames instead of scanning the whole club;
- accepting both historical club-members response shapes;
- keeping the previous generated data if a temporary API failure occurs;
- writing `generated/api-status.json` so the dashboard and GitHub Actions show whether the API sync actually succeeded;
- changing the scheduled refresh to every 12 hours, matching Chess.com's documented club-member cache behavior more closely.

After uploading V3.4, run **Actions → Update ACFA Data → Run workflow** once.


## V3.5 asset update
- Added `assets/images/acfa-champions-podium.png`.
- Converted the supplied podium artwork to transparent PNG.
- Added the podium artwork to the Tournament → Champions Podium section.
- Updated the service-worker cache to include the new asset.
