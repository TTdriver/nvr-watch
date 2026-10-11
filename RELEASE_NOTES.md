# NVR Watch 1.0.0

Initial packaged release of the existing NVR Watch portal.

- Preserves camera search, live views, per-camera archive browsing, calendar/timeline navigation and playback controls.
- Prepares the selected recording segment as an MP4 automatically, with Cancel during preparation.
- Adds administrator-only BI connection settings, masked saved credentials, connection testing and camera-list refresh settings.
- Keeps settings and encrypted credentials in a persistent Docker volume.
- Adds Docker Compose, Portainer instructions, health checks, source builds and GHCR publishing.

Browser playback is video-only. MP4 downloads retain recorded audio when available. Verified against Blue Iris 6 on Wine; the Windows reference recorder was unreachable during this release's real-recorder checks. Docker integration uses a separate fake BI fixture to verify container startup, configuration, encryption and recreation.

Shared as-is, at your own risk. Blue Iris and its license are not included.
