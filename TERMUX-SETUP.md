# Running HRECOS Dashboard on Android (Termux)

## One-time setup

```bash
# 1. Install Termux from F-Droid (not Play Store — Play Store version is outdated)
# 2. Open Termux and run:

pkg update && pkg upgrade -y
pkg install python git curl -y

# 3. Clone the repo
git clone https://github.com/Strobingn/hrecos-dashboard
cd hrecos-dashboard

# 4. Run
./run_termux.sh
```

## Access the dashboard

- **On the phone itself:** Open browser → `http://localhost:8080`
- **From another device on your WiFi:** `http://<your-phone-ip>:8080`
  (the script prints your local IP on startup)

## Notes

- First run installs deps automatically (~60 seconds)
- Subsequent runs start in ~5 seconds
- Uses SQLite — no database server needed
- Fetches live data from USGS, NOAA, and NDBC — no API keys needed
- All temps in °F, wind in mph, pressure in inHg
- ML anomaly detection is disabled (requires pandas — too heavy for ARM)
  Threshold-based alerts still work

## Troubleshooting

**Port already in use:**
```bash
pkill -f uvicorn; pkill -f "http.server"
./run_termux.sh
```

**pip install fails on a package:**
```bash
pip install --prefer-binary <package-name>
```

**Can't reach from other devices:**
- Make sure your phone and the other device are on the same WiFi
- Termux may need storage permission: `termux-setup-storage`

## Running in background (keep alive when Termux minimized)

```bash
pkg install termux-services -y
# Or simply use tmux:
pkg install tmux -y
tmux new -s hrecos
./run_termux.sh
# Detach: Ctrl+B then D
# Reattach: tmux attach -t hrecos
```
