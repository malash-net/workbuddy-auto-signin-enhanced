# workbuddy-auto-signin-enhanced

[English](./README.md) | [中文](./README.zh-CN.md)

> **⚠️ Vibe coded — use with caution.**
> Built through AI-assisted vibe coding and not audited for production use. Review before deploying in any critical context.

Runs [workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin) in Docker, on machines without the desktop client. Upstream is cloned at build time and never modified.

## Usage

Sign in (defaults to `auto`):

```bash
docker run --rm -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest
```

Other actions are passed straight through:

```bash
docker run --rm -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest status
```

Scheduled runs:

```cron
5 0 * * * docker run --rm -v /srv/workbuddy:/auth ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest >> /var/log/wb.log 2>&1
10 8 * * * docker run --rm --entrypoint python3 -v /srv/workbuddy:/auth ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest refresh.py >> /var/log/wb-refresh.log 2>&1
```

Mount a **directory**, not a single file.

## Exporting the credential

Run on a machine with the WorkBuddy client installed:

```bash
python3 export.py -o ~/workbuddy.json
scp ~/workbuddy.json nas:/srv/workbuddy/workbuddy.json
rm ~/workbuddy.json
```

## Refreshing the credential

```bash
python3 refresh.py -f ~/workbuddy.json           # skips while >7 days remain
python3 refresh.py -f ~/workbuddy.json --force
```

Or in the image:

```bash
docker run --rm --entrypoint python3 -v /srv/workbuddy:/auth \
  ghcr.io/malash-net/workbuddy-auto-signin-enhanced:latest refresh.py
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `WORKBUDDY_AUTH_FILE` | `/auth/workbuddy.json` | Credential file both scripts read and write |

## Security

`workbuddy.json` holds plaintext tokens — treat it as a password. Keep it out of git and public directories, and delete exported copies once transferred.

## License

[MIT](./LICENSE)
