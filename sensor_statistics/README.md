# Sensor Statistics

Adds a **Sensor Statistics** panel to the Home Assistant sidebar. Pick any sensor and see its long-term
averages, min and max over the last day, week, month, year or up to five years. Pick a second sensor to
compare the two.

## What you get

- Line chart of the average, with an optional min/max band
- Summary cards per sensor: average, lowest and highest value (with date), data point count
- Comparison card: average difference (first − second), largest gap, correlation
- Monthly breakdown table with a difference column when comparing
- Different units are fine: the second sensor gets its own axis on the right
- Resolution is automatic (hourly, daily, weekly) or can be set manually

## Data source

The panel reads Home Assistant's **long-term statistics**, which the recorder keeps indefinitely and
which are separate from the state history that gets purged. Only entities with a `state_class` such as
`measurement` have them, which covers practically all temperature, humidity and power sensors. If a
sensor is missing from the list, check that it has a `state_class`.

## Add to an existing app repository

This folder is self-contained, so it can live in a repository that already holds other apps or projects.

1. Copy the `sensor_statistics/` folder into your repository, either at the root or inside any subfolder.
   Home Assistant finds apps by searching the whole repository for `config.yaml`.
2. Make sure the repository root has a `repository.yaml`. If it does not have one yet, add:

   ```yaml
   name: My Home Assistant Apps
   url: https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY
   maintainer: Your Name
   ```

3. Commit and push. In Home Assistant open **Settings → Apps → App store**, use the three-dot menu →
   **Check for updates**, and the app shows up next to your other apps. If the repository is not added
   yet, add its URL under **Repositories** first.

Things to watch in a repository that also holds non-Home-Assistant projects:

- Home Assistant treats every `config.yaml`, `config.yml` or `config.json` it finds as an app definition,
  so avoid files with those names elsewhere in the repository unless they really are apps.
- The `slug` in `config.yaml` (`sensor_statistics`) must be unique among the apps in the repository.
- Each app is built from its own folder, so nothing outside this folder is needed to build it.

## Develop locally

The backend talks to Home Assistant over its WebSocket API. Outside of Home Assistant, point it at your
instance with a long-lived access token (profile page → Security):

```
pip install aiohttp
export HA_URL=http://homeassistant.local:8123
export HA_TOKEN=<long-lived access token>
python3 server.py
```

Then open http://localhost:8099. On Windows PowerShell use `$env:HA_URL = "..."` instead of `export`.

## Files

| File | Purpose |
| --- | --- |
| `config.yaml` | App definition (ingress, sidebar panel, Home Assistant API access) |
| `Dockerfile`, `run.sh` | Container image and start script |
| `server.py` | aiohttp backend: `/api/sensors`, `/api/statistics`, serves the frontend |
| `static/index.html` | The whole frontend (vanilla JS) |
| `static/chart.umd.js` | Bundled Chart.js 4, so the panel works without internet access |
