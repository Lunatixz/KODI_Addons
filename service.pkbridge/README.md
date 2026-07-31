# PKBridge — Plex-to-Kodi Bridge

A Kodi service addon that emulates a Plex Media Server. Any Plex client can connect to PKBridge and browse/play your Kodi library — no real Plex server needed.

## Features

- Full Plex API emulation (library, metadata, search, hubs, sessions, playlists)
- HTTP streaming (Plex app streams directly from Kodi files)
- Kodi local playback mode (`?pkbridge=1`)
- GDM network discovery (auto-detected on LAN)
- HTTPS support for plex.tv auth interception
- Mock plex.tv/link page for QR code sign-in flow

## Installation

1. Download or clone this repository
2. Copy the `service.pkbridge` folder to your Kodi addons directory:
   - **Windows:** `%APPDATA%\Kodi\addons\`
   - **macOS:** `~/Library/Application Support/Kodi/addons/`
   - **Linux:** `~/.kodi/addons/`
   - **Android:** `Android/data/org.xbmc.kodi/files/.kodi/addons/`
3. Restart Kodi
4. Enable the addon in **Settings → Addons → Services**

## Quick Start (Manual Connection)

If your Plex app supports manual server entry:

1. Note your Kodi machine's local IP (e.g., `192.168.1.100`)
2. In your Plex app, add a manual server at: `192.168.1.100:32400`
3. Use any token (or leave blank)

This works for most Plex apps including Plex for Android TV, iOS, web, etc.

## Setup for Apps Without Manual Server Entry (e.g., Dispatch)

Some Plex apps (like Dispatch) only support plex.tv sign-in and don't allow manual server entry. PKBridge includes a plex.tv auth interceptor that requires DNS redirect.

### How It Works

1. PKBridge mocks plex.tv auth endpoints on your local network
2. You configure DNS to redirect `plex.tv` traffic to your PKBridge server
3. The Plex app authenticates against PKBridge (fake auth, always succeeds)
4. The app then connects to PKBridge for your Kodi library

**Note:** If Kodi and the Plex app are on the same device, use `127.0.0.1` as the redirect target instead of your LAN IP.

### Platform-Specific DNS Setup

#### Android TV (Recommended: DNS Changer App)

No root required. Install a DNS changer app that supports per-app routing.

1. Install **[Personal DNS Filter](https://play.google.com/store/apps/details?id=dnsfilter.android)** from the Play Store
   - Alternative: **[DNS Changer](https://play.google.com/store/apps/details?id=com.jumodigital.cloudflare)**
2. Open the app and set DNS to your PKBridge server IP (e.g., `192.168.1.100`)
3. In the app's filter settings, enable DNS redirect **only for Dispatch** (or your Plex app)
4. Launch Dispatch and sign in via plex.tv/link

This only redirects DNS for the selected app — all other apps use your normal DNS.

#### Same Device (Kodi + Plex App on Same Machine)

If Kodi and the Plex app (e.g., Plex Desktop, web browser) are on the same device, use `127.0.0.1` (localhost) instead of your LAN IP.

**Windows:**
Add to hosts file (`C:\Windows\System32\drivers\etc\hosts`):
```
127.0.0.1  plex.tv
```

**macOS/Linux:**
Add to `/etc/hosts`:
```
127.0.0.1  plex.tv
```

**Android:**
Use a DNS changer app and set DNS to `127.0.0.1` (requires app that supports localhost).

**Set PKBridge setting:** DNS Redirect IP → `127.0.0.1`

This routes plex.tv traffic to PKBridge running on the same machine.

#### Windows

**Option A: Hosts File (per-device)**

1. Notepad as Administrator: Right-click Notepad → Run as administrator
2. Open `C:\Windows\System32\drivers\etc\hosts`
3. Add this line at the end:
   ```
   192.168.1.100  plex.tv
   ```
4. Save the file
5. Flush DNS cache: Open Command Prompt as admin, run `ipconfig /flushdns`

To undo: Remove the line you added and flush DNS again.

**Option B: PowerShell (one command, reversible)**

Run as Administrator:
```powershell
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "`n192.168.1.100  plex.tv"
ipconfig /flushdns
```

To undo:
```powershell
$h = Get-Content "C:\Windows\System32\drivers\etc\hosts"
$h | Where-Object { $_ -notmatch "plex\.tv" } | Set-Content "C:\Windows\System32\drivers\etc\hosts"
ipconfig /flushdns
```

#### macOS

1. Open Terminal
2. Edit hosts file:
   ```bash
   sudo nano /etc/hosts
   ```
3. Add this line:
   ```
   192.168.1.100  plex.tv
   ```
4. Press `Ctrl+O` to save, `Ctrl+X` to exit
5. Flush DNS cache:
   ```bash
   sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
   ```

To undo: Remove the line you added and flush DNS again.

#### Linux

1. Edit hosts file:
   ```bash
   sudo nano /etc/hosts
   ```
2. Add this line:
   ```
   192.168.1.100  plex.tv
   ```
3. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`)

DNS changes take effect immediately on Linux.

#### Router-Level (All Devices)

If your router supports conditional DNS forwarding:

1. Access your router admin panel (usually `192.168.0.1` or `192.168.1.1`)
2. Find DNS settings (may be under LAN, DHCP, or Advanced)
3. Add a conditional forward: `plex.tv` → `192.168.1.100`
4. Save and reboot router

This redirects plex.tv for ALL devices on your network. Only use this if all devices should connect to PKBridge.

**Supported routers:** ASUS (with Merlin firmware), pfSense, OpenWrt, pi-hole, AdGuard Home

## PKBridge Server Settings

Open Kodi → **Settings → Addons → Services → PKBridge**:

| Setting | Description |
|---------|-------------|
| Server Name | Display name shown to Plex clients |
| Server Port | Default: 32400 (standard Plex port) |
| Enable GDM Discovery | Auto-discovery on LAN via UDP multicast |
| DNS Redirect IP | Your PKBridge server IP (used in server responses) |

**Important:** Set the DNS Redirect IP to your server's LAN IP (e.g., `192.168.1.100`). This tells Plex clients where to connect for library content.

## Troubleshooting

### Plex app can't find the server
- Verify PKBridge is running (check Kodi logs)
- Ensure port 32400 is not blocked by firewall
- Try manual connection first to verify basic connectivity

### Sign-in fails (Dispatch, etc.)
- Verify DNS redirect is working: visit `https://plex.tv` in a browser on the same device — it should show PKBridge's page
- Check that HTTPS is enabled (look for "HTTPS server started" in Kodi logs)
- Ensure the DNS changer app is running and filtering the correct app

### Library shows empty
- Open PKBridge settings and verify Kodi library is scanned
- Check Kodi logs for JSON-RPC connection errors

### Playback fails
- PKBridge streams files directly over HTTP — ensure the Plex app supports the file format
- For direct Kodi playback, add `?pkbridge=1` to stream URLs

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Plex App   │────▶│  PKBridge    │────▶│  Kodi       │
│  (Dispatch) │     │  Port 32400  │     │  JSON-RPC   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  plex.tv    │
                    │  (mocked)   │
                    └─────────────┘
```

## License

GPL v3 — See [LICENSE](LICENSE) for details.
