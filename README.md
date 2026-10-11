# NVR Watch

A standalone Blue Iris web portal for live cameras and recorded footage. Choose a camera, pick a day, and jump to a moment on the timeline. Download an entire listed recording segment as an MP4 with one click.

This is a personal project that worked with Blue Iris 6 on Linux under Wine. It is shared as-is, at your own risk. The portal uses BI's web API, so its Docker host can be a different computer from the recorder. A Windows BI deployment has not yet been verified. Blue Iris, its license, UI3, cameras and footage are not included. This project is not affiliated with the Blue Iris vendor.

## What you get

- Camera search and live views.
- Per-camera archives, a recording-day calendar and a day timeline.
- Seeking, ten-second skip buttons, playback speed and adjacent-recording continuation.
- MP4 preparation and automatic downloading, with Cancel while preparing.
- An administrator settings page with connection testing.
- Persistent, encrypted BI credentials and a configurable camera-list refresh interval.
- Docker Compose and Portainer deployment, health checks and versioned container images.

**Browser playback currently has no audio. Downloaded MP4s include recorded audio when present.** The current browser player uses BI's MJPEG stream, which carries video only. MP4s can retain HEVC/H.265 and need a player that supports the recording's codec.

## How it works

```text
Browser → NVR Watch → Blue Iris web API → cameras and recordings
```

NVR Watch owns its interface, web server and sign-in flow. BI owns camera connections, recording, storage and retention. No UI3 files or libraries are loaded. UI3 may remain installed alongside it.

Each visitor signs in using their own BI account, and BI's camera/clip permissions still apply. The BI account saved in Settings is used for connection tests and the administrator's “Open playback” button. It is not exposed to ordinary visitors and does not give them automatic access to cameras.

BI passwords are never returned by the settings API. Saved passwords are encrypted with Fernet; the key and configuration live in the same protected Docker volume. Back up both together. Administrators with access to that volume can recover the credentials. Login passwords and BI session tokens are not logged, and BI tokens stay in server memory.

## Requirements

- Docker Engine with Docker Compose v2, or Portainer on a standalone Docker host.
- A working Blue Iris web server reachable from the Docker host.
- A BI account with access to the cameras and recordings you want to view.
- A current web browser.

For MP4s, enable the BI account permission to create/export clips. Automatic deletion of completed temporary exports also requires BI's clip-delete permission. Without it, generated copies may remain in BI's Clipboard folder. NVR Watch only requests deletion of its verified generated products; original recordings are kept.

## Prepare Blue Iris

In BI Settings → Web server, enable the web server and note its port. Keep authentication required. Create or use an account in BI Settings → Users with the necessary camera and clip access.

Verify that the BI web page works from the Docker host's network. Use the recorder's actual address and web-server port. When BI runs on another computer, `127.0.0.1` inside a Docker container refers to that container, not the recorder.

If you use HTTPS, BI must present a certificate trusted by the container. Certificate validation is enabled. The portal does not configure BI, install cameras, change firewall rules or alter recording/storage settings.

## Install with Docker Compose

On your Docker host:

```bash
mkdir -p nvr-watch
cd nvr-watch
curl -fsSLO https://raw.githubusercontent.com/TTdriver/nvr-watch/v1.0.0/compose.yaml
docker compose up -d
docker compose logs nvr-watch
```

The first startup prints an **Initial administrator access code** in the container logs. Save that code privately; it protects the settings page and is also stored in the persistent data volume. It is generated separately for every installation and is not embedded in the image.

Open:

```text
http://DOCKER_HOST_ADDRESS:8090/settings.html
```

Enter the administrator access code, then:

1. Choose HTTP or HTTPS.
2. Enter your BI IP address or hostname, without a protocol or port in that field.
3. Enter the BI web-server port.
4. Enter the existing BI username and password.
5. Click **Test connection**.
6. Click **Save settings**, then **Open playback**.

The password field becomes empty after saving. “Saved — leave blank to keep it” means the encrypted password is retained. Enter a replacement only if you want to update it.

Other visitors use `http://DOCKER_HOST_ADDRESS:8090/` and sign in with their own BI accounts. BI administrators can access Settings after signing in; ordinary BI users cannot. The local administrator access code also works when BI is unavailable.

To check the container:

```bash
docker compose ps
docker compose logs --tail=50 nvr-watch
```

The health check verifies the portal itself. A disconnected BI server does not make the portal unhealthy, so you can still open Settings and fix the connection.

## Install with Portainer

In a standalone Docker environment, open **Stacks → Add stack**. Name the stack `nvr-watch`. Paste the contents of this repository's `compose.yaml` into the Web editor and deploy it.

Use **Containers → nvr-watch container → Logs** to find the initial administrator access code. Then open the Docker host on port 8090 and configure the recorder as described above.

The Compose file uses a named volume for `/data` and `restart: unless-stopped`. There are no fixed IP addresses, custom subnets or `ipam` settings. Docker chooses the normal network from the host's configured address pools. The Docker host's existing network configuration must already avoid overlap with your LAN/VLANs.

If port 8090 is occupied, set `NVR_WATCH_PORT` in Portainer's stack environment variables, or put this in a local `.env` file for Compose:

```text
NVR_WATCH_PORT=8091
```

The application still listens on 8090 inside its container.

## Persistent settings and updates

The named `nvr-watch-data` volume stores `settings.json`, `encryption.key` and `admin-access-code`. Settings survive container restart, removal/recreation and upgrades as long as that volume is retained. Do not use `docker compose down --volumes` on an installation whose settings you want to keep.

To update, select the desired published version by setting `NVR_WATCH_TAG` in `.env` or Portainer's stack variables. Then:

```bash
docker compose pull
docker compose up -d
```

For example, the initial release uses `NVR_WATCH_TAG=1.0.0`. `latest` follows the newest published version. Versioned tags are preferable when you want a specific release.

Settings changes do not rebuild the image or require a container restart. Changing the recorder address resets playback sign-ins so users authenticate against the new recorder.

### Back up settings

Run from your Compose folder while the container is running. Avoid changing Settings during the backup:

```bash
umask 077
docker compose exec -T nvr-watch python -c "import tarfile,sys; tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz').add('/data',arcname='data')" > nvr-watch-settings.tar.gz
```

Protect the backup: it includes the encryption key and administrator access code. It does not include camera footage.

To restore your own trusted backup to a running deployment, then reload it:

```bash
docker compose exec -T nvr-watch python -c "import tarfile,sys; tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz').extractall(path='/',filter='data')" < nvr-watch-settings.tar.gz
docker compose restart nvr-watch
```

## MP4 downloads and Cancel

Click the arrow beside a recording. BI prepares the whole listed segment. Its button shows preparation progress and an **×** to cancel. When ready, the MP4 download starts automatically. Once the browser transfer starts, use the browser's download controls to cancel it.

BI writes a temporary export in its managed storage. After a successful transfer, the portal asks BI to remove that generated copy. It also retries cleanup for cancelled exports. Native conversion can briefly continue after cancellation, even though the portal stops the requested download.

Exports request the main stream without re-encoding. BI may require conversion for some recording types, and start/end boundaries can follow nearby keyframes. Large hourly recordings can take time and require temporary free storage on the recorder.

Abandoned exports are checked for cleanup after an hour while the service and BI session remain available. Restarting the portal loses its in-memory export tracking; interrupted copies may then require manual cleanup in BI's Clipboard view.

## Troubleshooting

**The settings page asks for a code.** Read the initial code from container logs, or recover it from your protected volume/backup. With Compose:

```bash
docker compose exec -T nvr-watch cat /data/admin-access-code
```

Keep the result private. A BI administrator can also sign in normally and access Settings.

**Cannot reach Blue Iris.** Check the recorder address, selected protocol and port. Confirm its web server is enabled. Test from the Docker host, then check Windows Firewall and routing/firewall rules between VLANs. Use an address reachable by the container; browser access from a different network does not prove container access.

**Username or password rejected.** Use a BI user account, not the Windows account. Check its access restrictions in BI. A blank saved-password field preserves the existing credential; enter the corrected password explicitly.

**HTTPS certificate verification failed.** Use a trusted BI certificate or install its issuing CA in a derived container image. The portal does not silently bypass certificate checks.

**Camera works in BI but is missing here.** Check that the signed-in BI account has permission for that camera and its recordings.

**Settings disappeared.** Confirm the same Docker volume is mounted at `/data`. Changing the Compose project/Portainer stack name can create a different volume. Restore the original volume or your backup.

**The portal needs a new sign-in.** BI restarts, portal restarts and recorder-address changes invalidate sessions. Sign in again.

**There is no browser audio.** This version uses video-only MJPEG playback. Available audio is preserved in MP4 downloads.

This deployment uses local-network HTTP. For remote access, put the portal behind an HTTPS reverse proxy. The project does not open router ports or configure remote exposure.

## Run without Docker

The original Python service remains supported. You need Python 3.10 or newer with venv support and the pinned dependencies. On Debian/Ubuntu, install `python3-venv` if Python reports that ensurepip is missing:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py --port 8090 --data-dir ./data
```

Configure the recorder through `/settings.html` using the generated access code. On Windows, create the environment with `py -3 -m venv .venv` and use `.venv\Scripts\python.exe` instead. No Linux system service is installed by these commands.

The optional `install.py` installer installs a Linux user service. Its application files go in `~/.local/share/nvr-watch/`, persistent settings in `~/.config/nvr-watch/`, and its service in `~/.config/systemd/user/nvr-watch.service`. It starts with the user manager, normally at login. It does not configure automatic desktop login. See `python install.py --help`.

## Source, builds and verification

The source is in this repository. To build locally rather than pull GHCR:

```bash
git clone https://github.com/TTdriver/nvr-watch.git
cd nvr-watch
docker compose -f compose.build.yaml up --build -d
```

Run Python checks with `python test.py` and frontend checks with `node web/core.test.mjs`. `compose.test.yaml` and `tests/fake-bi.py` are isolated CI fixtures, not deployment instructions for a real recorder.

GitHub Actions tests the app, builds and starts Docker Compose, verifies encrypted settings and connection testing against a fake BI service, recreates the container, then verifies persistence. Pushing a version tag such as `v1.0.0` publishes `ghcr.io/ttdriver/nvr-watch:1.0.0` for AMD64 and ARM64 after those checks pass. The base image, Python dependency and Actions revisions are pinned.

Real BI 6 checks verified camera access, old-footage playback, connection testing, MP4 attachment delivery with HEVC video/AAC audio, and removal of generated export copies. Playback position is estimated from elapsed playback time, so recordings with gaps can differ from the displayed clock. Times use the browser's timezone.

A source-only ZIP can be generated with `python build-package.py`. It excludes instance settings, credentials, logs, Wine prefixes and footage. To ask your own AI to install it, copy [AI-SETUP.md](AI-SETUP.md); that prompt is separate from these human instructions.

Technical references: [Docker volumes](https://docs.docker.com/reference/compose-file/volumes/), [GHCR publication](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images), [credential encryption](https://cryptography.io/en/stable/fernet/).
