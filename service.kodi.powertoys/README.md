# Kodi PowerToys

Automated library maintenance for Kodi: scraping, refresh, cleaning, texture cache, backup, music, network sync, QR-coded remote actions, and system upkeep.

Documents **PowerToys v1.3.7**.

## Features

| Feature | Description |
|---|---|
| **Scraping** | Scheduled scans of TV/movie source folders for new content. Source paths are auto-detected from Kodi's configured video sources on first run (only fills empty settings; always editable) |
| **Refresh** | Periodic metadata refresh. Art-only mode targets items missing poster/fanart; the QA option additionally flags blank plot/MPAA *within* art-only mode |
| **Cleaning** | Removes missing files and duplicate entries (quality-weighted, IMDb-aware). Runs after scans or on schedule; exclude list protects chosen titles |
| **Texture cache** | Prunes orphaned artwork rows from network-path textures and clears stale rows whose cached file is gone, so Kodi re-fetches artwork lazily on next view. Optional disk deletion of orphaned thumbnail files |
| **Backup** | Scheduled library export into timestamped folders with keep-N rotation |
| **Music** | Scheduled music library scan with optional clean-after |
| **Sync** | Peer sync over LAN: UI refresh broadcast, watched/resume state sync, scan-command push with offline retry, Wake-on-LAN |
| **QR Actions** | Build JSON-RPC command packages on a webpage, generate a QR code, scan with your phone to execute on any discovered Kodi instance |
| **Share watcher** | Detects when a configured network share recovers and auto-rescans it |
| **System upkeep** | System cache cleanup, Free RAM tool, log viewer, health report |

All destructive operations honor **Dry Run** (enabled by default). Physical file deletion additionally requires its own opt-in toggle (see Settings). Every delete action that shows a prompt asks for confirmation first, whether Dry Run is on or off.

---

## Quick Start

1. **Settings → Scraping** — turn on the scraper. TV/Movie source paths are auto-detected from your Kodi video sources; just confirm they look right.
2. **Settings → Cleaning** — leave **Dry Run** on while you evaluate. Every scheduled and on-demand action previews what it would do without changing anything.
3. **Addons → Programs → Kodi PowerToys** — run *Library health report* for counts, missing files, duplicates, and next scheduled runs.
4. Switch on the feature categories you want (Refresh, Texture Cache, Music, Backup, Network Sync, QR Server). Each stays dormant until its toggle is on.
5. **Settings → Maintenance** — enable *PowerToys context menu actions* to get Clean/Season/Mark-watched items on library rows.

Tips:
- Set your Kodi **settings level to Advanced or Expert** (bottom of the settings window) to see every option below — Standard hides the advanced ones.
- New here? Keep Dry Run on for the first few runs and read the prompts/notifications before flipping it off.
- Everything scheduled skips itself while media is playing (unless you enable running during playback).

---

## Network Sync

Enabled by **Sync with network peers**. Discovery uses Kodi's own `_xbmc-jsonrpc-h._tcp` mDNS announcement, so **"Allow remote control via HTTP" must be enabled in Kodi (Settings → Services → Control)** on every instance. Discovery starts when either Sync or the QR server is enabled.

### What syncs

| Message | Trigger | Behavior |
|---|---|---|
| **UI refresh** | A scan batch finishes | `Container.Refresh` on all online peers **once per batch** — coalesced: the broadcast waits until scans go quiet (10s with no scan-finished events and nothing still queued) instead of flickering per directory scanned; ack + up to 3 retries (15s timeout) |
| **Library scan** | A scan command is *received* (Programs menu, context menu, or QR `/exec` — not internal schedules) | Queued to **every known peer** with retry **until each confirms**; `path` propagates when the original command had one; peers that went dark are retried when they reappear (backoff 15s→15min), entries survive restarts, FIFO cap 50 |
| **Watched state** | Playback ends, or manual mark-watched (context/skin) | `playcount`/`lastplayed`/`resume` pushed keyed by **file path** (DB IDs differ per instance); batched into one pending entry; newest `lastplayed` wins (skips only when the local timestamp is strictly newer); a 2s local suppression window prevents push-back loops |
| **Wake-on-LAN** | First failed push (debounced 60s), `POST /wake`, or QR `PowerToys.Wake` | Magic packets for every MAC in the Wake-on-LAN setting |

Notes and limits:
- Pushes need **the sender's own Kodi webserver enabled** (acknowledgements return over HTTP).
- A peer running Kodi **without PowerToys** accepts the message but never confirms; sends back off at a 15-minute backoff until shed from the queue.
- Scheduled runs stay per-instance — a scan *command* propagates, an internal schedule does not.
- Receiver instances honor their own settings (a full scan push requires the peer's scraper to be enabled).

### Wake-on-LAN

Set **Wake-on-LAN MAC addresses** (comma-separated) in Sync settings — one per device you want woken. Packets are broadcast, so each NIC picks up its own; targets don't need matching names. Enable WOL in the target device's BIOS/OS as usual.

---

## QR Action Server

A built-in web page for stacking JSON-RPC commands into QR codes.

### How it works

1. Enable the server: **Settings → QR Server → Enable QR server**
2. Open the builder: `http://<your-kodi-ip>:9095/`
3. Add commands from the method dropdown (Video Library, Audio Library, Input, System, GUI, Files, Add-ons, Profiles, Player, PowerToys, or custom JSON-RPC)
4. **Params render as controls, not raw JSON**: each parameter gets the right input — dropdowns for library IDs (movies, shows, episodes, seasons, artists, albums, profiles, add-ons, sources, playlists, active players) fetched **live from this Kodi instance**, enums from `JSONRPC.Introspect` (with curated fallback lists for action/window IDs, sort methods and order, and media types — schema enums always win when present), **checkbox lists for `properties`**, typed sub-fields for structured objects like **`sort`/`limits`** (enum selects, start/end numbers), number/boolean/JSON fields by type, required params marked with `*`. Episode/season dropdowns follow the selected show. **Edit as JSON** flips to the raw textarea for anything unusual — *Custom value…* in any dropdown also lets you type freely
5. Stack, reorder, remove; preview the JSON
6. **Generate QR Code** — the QR encodes `http://<ip>:9095/run/<encoded-commands>`; a **Share…** button appears on Android (native share sheet) to send the link without scanning
7. Scan with a phone camera → landing page shows the decoded commands, a multi-select of discovered Kodi instances, and **Execute**
8. Results display per instance

### Example use cases

- Trigger a library scan on every box after adding content to a shared NAS
- Wake the whole fleet (`PowerToys.Wake`), then send the scan
- Play a specific file on a specific box (`Player.Open`)
- Set volume, take a screenshot, switch profiles, simulate remote input

### QR server settings

| Setting | Default | Description |
|---|---|---|
| Enable QR server | Off | Master toggle |
| QR server port | 9095 | HTTP listen port (separate from Kodi's 8080) |
| Require login | Off | HTTP Basic Auth for all endpoints |
| Username / Password | — | Credentials the phone's browser will prompt for |

---

## API Reference

All endpoints ride the server's Basic Auth (when enabled).

### `GET /`
Builder page.

### `GET /run/<encoded>`
Landing page for scanned QR codes; decodes commands and presents the execution UI.

### `POST /exec`
Executes JSON-RPC commands on selected instances.

```json
{
  "commands": [{"jsonrpc": "2.0", "method": "System.SetVolume", "params": {"volume": 50}}],
  "instances": [{"ip": "192.168.1.100", "port": "local", "self": true},
                 {"ip": "192.168.1.101", "port": 8080}]
}
```

Response reports `ok`/`error` per instance. `VideoLibrary.Scan` commands sent here also queue the peer scan push. The pseudo-command `{"method": "PowerToys.Wake"}` wakes configured MACs.

### `GET /api/v1/qr?commands=<json>`
Returns an encoded URL ready for QR generation:

```json
{"url": "http://192.168.1.100:9095/run/...", "encoded": "...", "commands": [...]}
```

### `GET /api/v1/instances`
Discovered instances (this device plus zeroconf peers).

### `GET /api/v1/schema?method=<jsonrpc-method>`
Parameter descriptors for a method, derived from `JSONRPC.Introspect`: name, type, required flag, description, and enum values when the schema defines them (enums resolve inline, via array items, or through `$ref` type lookups).

```json
{"method": "Input.ExecuteAction", "description": "…",
 "params": [{"name": "action", "required": true, "type": "string"}]}
```

### `GET /api/v1/options?kind=<kinds>[&tvshowid=<id>]`
Live value lists for dropdowns, fetched from this Kodi instance. Kinds: `movies`, `tvshows`, `episodes` (all episodes, or just one show with `tvshowid`), `seasons` (requires `tvshowid`), `artists`, `albums`, `profiles` (includes `name` for `Profiles.LoadProfile`), `addons`, `sources` (video paths), `playlists`, `players` (active players, with 0/1 fallback).

```json
{"options": [{"value": 42, "label": "Blade Runner (1982)"}]}
```

### `POST /wake`
Sends Wake-on-LAN packets for every configured MAC: `{"woken": 2}`.

### `GET /log`
Serves `special://logpath/kodi.log` as plain text. Parameters: `?file=old` for `kodi.old.log`, `?lines=N` to tail the last N lines (read capped at 2MB from the end).

### `GET /report`
The library health report as an HTML page (phone-friendly).

---

## Programs Menu

Addons → Kodi PowerToys (Programs). Nine actions:

| Item | Notes |
|---|---|
| Run scraper now | Requires **Enable Scraper** |
| Run refresh now | Requires **Enable Refresh** |
| Run clean now | Always works |
| Run texture maintenance now | Requires **Enable texture cache maintenance** |
| Run backup now | Requires **Enable scheduled library backup** |
| Run music scan now | Requires **Enable music library scan/clean** |
| Clean system cache | Sizes temp/packages/old logs, asks yes/no, then deletes — **Dry Run blocks the deletes** (active `kodi.log` is never touched) |
| Free RAM now | Python garbage collection + platform memory trim + own-cache drop |
| Library health report | Always works |

Items whose feature toggle is off are silently skipped by the service. Long actions started from this menu show a busy/progress indicator while they run; scheduled and background automation runs stay silent.

---

## Context Menu

Enabled by **Enable context menu actions** (off by default — enable it first). Items appear on the highlighted entry:

| Item | Visible on | Action |
|---|---|---|
| PowerToys: Clean this show | TV shows | Removes missing episodes + duplicate entries for that show |
| PowerToys: Remove this movie | Movies | Removes the selected movie entry (and file, per gates) |
| PowerToys: Clean this movie | Movies | Cleans the clicked movie's whole duplicate group |
| PowerToys: Delete this season | **Season rows only** | See Season Cleanup below |
| PowerToys: Remove this episode | **Episode rows only** | Removes the selected episode entry (and file, per gates) |
| PowerToys: Mark season watched | **Season rows only** | Watched/unwatched choice applied to every episode in the season |
| PowerToys: Mark show watched | TV shows | Watched/unwatched choice applied to every episode in the show |
| PowerToys: Remove this show | TV shows | Removes every season/episode entry plus the show itself (files per gates) |
| PowerToys: Scan this folder | Files/video | Queues a scan of the selected path (and pushes it to peers) |
| PowerToys: Library health report | Everywhere | Same report as the Programs menu |

Confirmation prompts fire **immediately when you click** (before anything queues), and confirmed actions run at high priority in click order — so you can confirm one item after another without waiting on running scans or long tasks. Every prompt ends with an explicit action line stating exactly what confirming does: library removal, plus file deletion or "files kept on disk" based on your Allow Media Deletion / Dry Run settings.

Every clean/mark action answers with a notification: how many entries were removed (or would be, under Dry Run), a "nothing to clean" notice when the item is healthy, or a "queued" notice if media is playing and the work will run after playback stops.

### Season cleanup

One action removes an entire season — both the files on disk and the library entries:

1. Select the season row → **Delete this season**
2. The prompt shows show, season, episode count, and total size, then states exactly what confirming does (library removal, file deletion per settings), prefixed `[DRY RUN]` when Dry Run is on
3. **One yes/no confirmation always appears**, regardless of the Dry Run setting
4. Deletion runs through the shared removal path, which enforces the gates:

| Dry Run | Allow Media Deletion | Result |
|---|---|---|
| On | (greyed out) | Nothing changes — entries and files both kept; the prompt runs as a preview |
| Off | Off | Library entries removed, files kept on disk |
| Off | On | Library entries removed **and** files deleted |

The offline-share guard also applies: if the item's network mount root is unreachable, removal aborts for that item.

---

## Health Report

Programs menu or context menu. Shows: TV/episode/movie counts, texture cache rows + bytes, missing files (first 25 + count), duplicate groups (first 25 + count), and next scheduled runs for scraper/refresh/backup/texture. A busy indicator shows while the report builds (it checks every episode's file, which can take a while on network shares); results are cached for 5 minutes so an immediate re-run answers instantly, and the cache is invalidated automatically when the library changes. Build failures surface as an error notification. Also available as a web page at `/report`.

---

## Scheduling & Playback Behavior

- **Service start delay** — dual purpose: startup wait *and* the idle threshold (seconds of global idle required before scheduled work runs when **Only run when Kodi is idle** is on).
- **Run tasks while media is playing** (off by default): while something is playing, clean/refresh tasks **pause mid-task and resume** when playback stops; scheduled backup, texture, music, and Free RAM runs are skipped until playback ends; an in-flight directory scan stops waiting.
- **Task persistence** — pending scrape/clean/refresh tasks survive Kodi restarts (cached for 28 days, invalidated on addon upgrade). Sync outbox entries (unconfirmed scans/watched updates) persist too.
- **Scan error retry** (off by default) — after a scan error, re-queues the scraper with a 1-hour cooldown.
- **Offline share alert** (off by default) — warns once per share per session when a configured SMB/NFS/FTP/WebDAV source root is unreachable. Independently, **any library-entry removal silently aborts** if its source root is offline (safety guard).
- **Debug logging** — Enable Debugging gates all log output below errors.

---

## Free RAM

**Free RAM now** (Programs menu) or scheduled via **Auto free RAM** (Maintenance settings, interval in hours). Each run:

1. Forces Python garbage collection (`gc.collect`) over Kodi's interpreter
2. Best-effort platform memory trim of Kodi's own process — glibc `malloc_trim` (Linux), `mallopt(M_PURGE)` (Android), working-set trim (Windows); unsupported platforms skip gracefully

Reports objects collected and free-memory before/after. Scope is honest: this frees **Kodi's own process** memory; Kodi's sandbox has no API to purge other apps.

---

## Settings Overview

### Scraping
Enable, TV/Movie source paths (auto-detected from video sources when empty), interval in days, progress dialog toggle.

### Refresh
Enable + interval. **Only refresh items missing artwork** restricts to items lacking poster/fanart; **blank plot/MPAA QA** is a sub-option that only applies inside art-only mode. Include Episodes in TV Refresh (default on), Ignore local NFO files when refreshing (default off), Clean during refresh (queues cleans per item *while* refreshing — distinct from "Clean Library after Scan").

### Cleaning
Clean after scan, exclude list (**comma-separated, case-insensitive, exact title match**), Dry Run (default on — blocks all removals), Also delete media files from disk (permanent — greyed out until Dry Run is off). Duplicate matching: movies by IMDb number when present, else label+year; episodes by show/season/episode. Quality weighting picks the master copy: 2160p/4K +50, 1080p +30, 720p +10, remux +20, x265/HEVC +15, x264 +5, local (non-network) path +5.

### Texture
Enable + interval. Pruning covers **network-path textures only** (smb/nfs/ftp/dav/sftp); local artwork is skipped. Re-caching works by deleting stale database rows whose image file is gone — Kodi re-fetches the artwork when next viewed (nothing is downloaded by the addon). **Also delete orphaned thumbnail files from disk** requires both itself on **and** Dry Run off.

### Music
Enable + interval (days), clean music library after scan.

### Backup
Enable, folder, interval, **Old backups to keep** (0 = unlimited). Each run exports into `powertoys-YYYYMMDD-HHMM/` inside the backup folder; only those subfolders are ever pruned, never your own files, only after a successful export, never when Dry Run is on.

### Sync
Enable peer sync, Wake-on-LAN MAC addresses (comma-separated).

### QR
Enable, port (9095), optional HTTP Basic Auth credentials.

### Maintenance
Enable PowerToys context menu actions (off by default; the first toggle in this category), retry scraper after scan error (1h cooldown), alert on offline shares, auto-rescan on share recovery (60s check; triggers when a configured share transitions offline→online), Auto free RAM + interval (hours).

### General
Run tasks while media is playing (defers instead of aborting — see above), only run when Kodi is idle (threshold = start delay), start delay (dual purpose), debugging.

---

## Network requirements

- All Kodi devices on the same LAN; mDNS/Bonjour working (no client isolation)
- **Allow remote control via HTTP** enabled on each device
- QR server port open in any firewall (default 9095)
- WOL: target devices configured for wake-on-LAN in firmware/OS

---

## Troubleshooting

**Peers not discovered:** check HTTP remote control on all boxes, mDNS on the network, and that Sync or QR server is enabled here.

**Scan push never delivers:** the peer needs PowerToys running to acknowledge; the sender's own webserver must be on for the ack path. Watch logs with debugging enabled.

**QR page won't load:** confirm the server is enabled and try `http://<kodi-ip>:9095/` directly.

**Context items missing:** the context-menu toggle is off by default (Maintenance settings).

**Commands fail on a remote instance:** that box's webserver may have different auth or a non-standard port — check its Services → Control settings.

**QR codes too large:** keep command packages small; longer URLs produce denser codes.
