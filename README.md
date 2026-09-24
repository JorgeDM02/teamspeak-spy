# teamspeak-spy

Poll a TeamSpeak 5 server (via its HTTP query API `serverlist` endpoint) and update a Discord webhook message with the current online user count.

<img width="401" height="135" alt="imagen" src="https://github.com/user-attachments/assets/765975ef-8fc8-4818-8558-1180b5ddc16d" />


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

Alternatively, you can setup a cronjob to achieve similar results:

```sh
cronjob -e
* * * * * path/to/script #Runs every minute
0 * * * * path/to/script #Runs on the first minute of every hour
```


Exit code `2` = missing/invalid config, `1` = TeamSpeak/Discord request failed (single-run mode). In `--interval` mode transient failures are logged and the loop continues; `Ctrl+C` stops cleanly.
