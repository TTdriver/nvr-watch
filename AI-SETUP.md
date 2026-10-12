# Copy this into your own AI assistant

This prompt installs the existing NVR Watch project against your own Blue Iris server. The human instructions are in README.md. Replace the bracketed values before pasting.

```text
Help me install NVR Watch from https://github.com/TTdriver/nvr-watch. Read the README and current Compose files first. Keep the existing application; do not rebuild its interface from scratch.

My Docker host is: [host and operating system]
My Blue Iris web-server URL is: [complete address and port]

Use the published versioned GHCR image and the project's compose.yaml. Keep the /data volume persistent, use the normal Docker network, and do not add a fixed subnet. Do not change my router, VLANs, BI recording/storage settings or existing footage.

Build the current source, start the container, verify its health, and open the first-run connection form. Let me enter the recorder details and my existing BI administrator credentials myself in the settings page. Do not use the older 1.0.0 prebuilt image for this flow. Verify Test connection, Save settings and playback. Settings must survive container recreation. If testing a download, use an existing short recording and remove only the generated export copy.

Explain the container address, persistent volume, updates and settings backup. Tell me that browser playback currently has no audio; MP4 downloads retain audio when available. Do not put my passwords, private network details, encryption key or footage in a repository or public report.
```
