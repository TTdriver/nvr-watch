# Existing-project review

The existing project is NVR Watch, an independent HTML/CSS/JavaScript frontend and Python HTTP adapter. This release extends that source rather than replacing the interface.

## What was already present

Camera search, live views, per-camera archives, recording-day calendar, timeline navigation, MJPEG playback, seek/skip/speed controls, adjacent-recording continuation, frame snapshots and MP4 preparation/download controls. Authentication used the existing BI account through its MD5 challenge protocol; upstream BI sessions remained server-side.

The application ran as a Linux user service. A persistent JSON file selected the BI URL, host and port. There was no browser settings page and no Docker configuration.

## What this release adds

An administrator settings page, persistent encrypted BI credentials, connection testing, configurable metadata refresh, Docker packaging and publishing workflows. Existing BI account sign-ins are preserved. Stored service credentials are available only to administrators through the saved-account sign-in action; they are never sent back to the browser.

The container keeps its configuration and encryption key under /data. First-run setup verifies a BI administrator account; later settings access uses the signed-in BI administrator session. CLI connection arguments can seed a new installation; saved web settings take precedence afterward.

## Current limits

Browser playback is silent MJPEG. MP4 exports preserve available audio and can retain HEVC. Playback time is estimated; gaps can differ from the displayed clock. BI performs the conversion and stores temporary products. If portal tracking is lost during a restart or BI permissions prevent deletion, an administrator may need to clean up the generated copy in BI's Clipboard view.

The original UI is retained. Camera and recorder configuration, storage retention, licensing, router settings and VLAN policy are outside the portal's scope.
