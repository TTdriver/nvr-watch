# NVR Watch

A web portal for Blue Iris live cameras and recorded footage. Browse recordings by camera and date, use the timeline to find a moment, and download recording segments as MP4 files.

## Requirements

- A Docker host with Docker Compose v2, or Portainer managing that host.
- A working Blue Iris web server reachable from the Docker host.
- A Blue Iris administrator account for initial setup.
- A current web browser.

Blue Iris, its license, cameras, and footage are not included. NVR Watch connects to the Blue Iris web API and does not change recording or storage settings.

## Prepare Blue Iris

1. Enable the web server in **Blue Iris Settings → Web server** and note its port. Keep authentication enabled.
2. Use an account with administrator access for initial setup.
3. Confirm the web server is reachable from the Docker host. Use the recorder's actual address; `127.0.0.1` inside a container refers to that container.

For MP4 downloads, the account needs permission to create/export clips. Automatic cleanup of temporary exports also requires clip-delete permission. Original recordings are retained.

## Install with Docker Compose

The current source uses first-run connection setup without a separate access code. The published `1.0.0` image predates this update, so build from source for the current flow:

```bash
git clone https://github.com/TTdriver/nvr-watch.git
cd nvr-watch
docker compose -f compose.build.yaml up --build -d
```

Open `http://DOCKER_HOST_ADDRESS:8090/` in your browser.

If port 8090 is already in use, create a `.env` file in the project folder:

```dotenv
NVR_WATCH_PORT=8091
```

Start the deployment again and open the selected port.

## Install with Portainer

Build the current source on the Docker host first:

```bash
git clone https://github.com/TTdriver/nvr-watch.git
cd nvr-watch
docker build -t nvr-watch:local .
```

In Portainer, select the Docker environment and open **Stacks → Add stack**. Name the stack `nvr-watch`, then paste this into the web editor:

```yaml
services:
  nvr-watch:
    image: nvr-watch:local
    pull_policy: never
    restart: unless-stopped
    ports:
      - "8090:8090"
    volumes:
      - nvr-watch-data:/data
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp:size=16m,mode=1777
volumes:
  nvr-watch-data:
```

Deploy the stack. If port 8090 is occupied, change the first port number, such as `"8091:8090"`. Open the Docker host at that port.

## First launch and sign-in

The first launch opens the recorder connection form:

1. Choose HTTP or HTTPS.
2. Enter the recorder's IP address or hostname, without a protocol or port.
3. Enter the Blue Iris web-server port.
4. Enter an existing Blue Iris administrator username and password.
5. Select **Test connection**, then **Save and open playback**.

Saving verifies administrator access, stores the connection, and signs you in. Future visitors sign in with their own Blue Iris accounts. Camera and recording permissions come from Blue Iris. Administrators can open **Settings** after sign-in; ordinary accounts cannot change the connection.

Saved passwords are encrypted and never returned to the browser. A blank password field keeps the saved password. Old access-code files are ignored by the current source.

## Persistent settings and backups

The named data volume stores the connection settings and encryption key. Keep the same volume when recreating or updating the container. Do not use `docker compose down --volumes` if you want to retain settings.

For a source-built Compose deployment, back up settings from the project folder:

```bash
umask 077
docker compose -f compose.build.yaml exec -T nvr-watch python -c "import tarfile,sys; tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz').add('/data',arcname='data')" > nvr-watch-settings.tar.gz
```

Protect this backup: it contains encrypted credentials and the key needed to decrypt them. It does not contain footage.

## Updates

For a source-built Compose deployment:

```bash
git pull --ff-only
docker compose -f compose.build.yaml up --build -d
```

For Portainer, rebuild `nvr-watch:local` from the updated source on the same Docker host, then redeploy the stack using the local image. Retain its data volume.

The separate `compose.yaml` uses published GHCR images. Until a newer release is published, its default `1.0.0` image still uses the older setup flow.

## Troubleshooting

- **Portal unavailable:** confirm the container is running, check its logs, and confirm the host port is available and reachable.
- **Blue Iris unavailable:** confirm its address, web-server port, authentication, and network access from the Docker host.
- **Sign-in rejected:** use a Blue Iris account. Initial setup and Settings require administrator access.
- **Settings requires sign-in:** sign in with a Blue Iris administrator account. It requires a reachable recorder.
- **Settings still asks for an access code:** you are using the older 1.0.0 image. Build the current source.
- **HTTPS connection fails:** use a certificate trusted by the container. Certificate validation is enabled.
- **Settings disappeared:** confirm the deployment still mounts its original data volume.

Browser playback currently uses video-only MJPEG. Downloaded MP4s retain available recorded audio and may require a player supporting the recording's codec. Large exports need time and temporary storage on the recorder. Interrupted exports may need manual cleanup in Blue Iris's Clipboard folder.

For remote access, use an HTTPS reverse proxy. This project does not configure router ports or remote access.

## Run without Docker

Python 3.10 or newer with venv support is required:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py --port 8090 --data-dir ./data
```

Open the portal and complete the same first-run setup. The optional Linux user-service installer is available through `python install.py --help`.

A source-only ZIP can be created with `python build-package.py`. It excludes instance settings, credentials, logs, and footage. For an installation prompt to give an AI assistant, see [AI-SETUP.md](AI-SETUP.md).
