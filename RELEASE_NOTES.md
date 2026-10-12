# Unreleased

- Replace the installation access code with first-run recorder connection setup.
- Verify a Blue Iris administrator account before saving, then sign that user in.
- Use Blue Iris administrator sessions for later Settings access; ordinary users retain their existing camera and recording permissions.
- Ignore old access-code files and remove the code authentication endpoint.
- Allow the Settings page to scroll to its action buttons and tighten header spacing.
- Update automated checks for first-run setup and administrator sign-in after container recreation.

The published 1.0.0 image is unchanged. Build the current source to use these updates.

# NVR Watch 1.0.0

Initial packaged release of the existing NVR Watch portal.

- Preserves camera search, live views, per-camera archive browsing, calendar/timeline navigation and playback controls.
- Prepares the selected recording segment as an MP4 automatically, with Cancel during preparation.
- Adds administrator-only BI connection settings, masked saved credentials, connection testing and camera-list refresh settings.
- Keeps settings and encrypted credentials in a persistent Docker volume.
- Adds Docker Compose, Portainer instructions, health checks, source builds and GHCR publishing.

Browser playback is video-only. MP4 downloads retain recorded audio when available. Verified against Blue Iris 6 on Wine; Windows BI has not yet been verified. Docker integration uses a separate fake BI fixture to verify container startup, configuration, encryption and recreation.

Shared as-is, at your own risk. Blue Iris and its license are not included.
