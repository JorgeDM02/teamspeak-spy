# teamspeak-spy

Poll a TeamSpeak 5 server (via its HTTP query API `serverlist` endpoint) and update a Discord webhook message with the current online user count.

<img width="397" height="138" alt="imagen" src="https://github.com/user-attachments/assets/e780fc64-02d8-498c-8583-35390d351335" />

## Setup

1. Install: `pip install .` (or `uv sync`)
2. Copy config: `cp .env.example .env` and fill in values.

| Var | Description |
| --- | --- |
| `TS_SERVER_NAME` | Title shown in the Discord embed |
| `TS_QUERY_API_KEY` | TeamSpeak HTTP query API key (`x-api-key` header) |
| `TS_HTTP_SERVER_IP` | Host or `http(s)://host` of the query API |
| `TS_HTTP_SERVER_PORT` | Port of the query API |
| `DISCORD_WEBHOOK_URL` | Discord webhook base URL (legacy `DISCORD_WEBOOK_URL` still works) |
| `DISCORD_MESSAGE_ID` | ID of the message to edit via `PATCH /messages/{id}` |

## Usage

Run once:

```sh
teamspeak-spy
```

Repeat every 60 seconds:

```sh
teamspeak-spy --interval 60
```

Exit code `2` = missing/invalid config, `1` = TeamSpeak/Discord request failed (single-run mode). In `--interval` mode transient failures are logged and the loop continues; `Ctrl+C` stops cleanly.
