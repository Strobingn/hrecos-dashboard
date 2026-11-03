# Legacy files

These are kept for reference only. Nothing in the active stack imports or serves them.

## `cornwall-pwa/`

An earlier standalone PWA ("Cornwall RiverWatch") that rendered hard-coded
readings and used Google Maps. It was never wired to the backend and was not
referenced by `docker-compose*.yml`, nginx, or CI.

Superseded by `frontend/index.html` (the served web dashboard) and `mobile/`
(the Expo Android app).

## `capacitor-wrapper/`

A Capacitor shell that pointed at a `www/` directory which no longer exists.
The Android app is maintained directly in `mobile/` with Expo.
