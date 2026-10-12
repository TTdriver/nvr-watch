# Install with an AI assistant

Copy this prompt and fill in your Docker host. Enter recorder credentials directly in the application.

```text
Help me install NVR Watch from https://github.com/TTdriver/nvr-watch.
Read README.md and the Compose files first.

My Docker host is: [host and operating system]

Install the published ghcr.io/ttdriver/nvr-watch:1.1.0 image using compose.yaml. Keep the /data volume persistent. If port 8090 is occupied, select
an available port using NVR_WATCH_PORT. Preserve the host's network settings.

Start the container and open the portal. Let me enter the Blue Iris address,
web-server port, and existing administrator credentials directly in the form.
After setup, users sign in with their own Blue Iris accounts.

Explain the portal address, settings backup, and how to update the deployment.
Do not put credentials, private connection details, settings files, or footage
in a repository. Do not change Blue Iris recording settings or router settings.
```
