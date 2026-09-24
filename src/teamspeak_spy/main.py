"""Poll a TeamSpeak 6 HTTP query API and update a Discord webhook message."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv, set_key, find_dotenv

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class SpyError(Exception):
    """Raised when polling TeamSpeak or updating Discord fails."""


@dataclass()
class Config:
    server_name: str
    query_api_key: str
    base_url: str
    webhook_url: str
    message_id: str
    timeout: int = DEFAULT_TIMEOUT


def _get_required(name: str, alternatives: tuple[str, ...] = ()) -> str:
    for key in (name, *alternatives):
        value = os.getenv(key)
        if value is not None and value.strip() != "":
            if key != name:
                logger.warning("Env var %s is deprecated, use %s instead.", key, name)
            return value.strip()
    raise ConfigError(f"Missing required env var: {name}")


def _build_base_url(host: str, port: str) -> str:
    host = host.strip().rstrip("/")
    port = port.strip()
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ConfigError(f"Invalid TS_HTTP_SERVER_PORT: {port!r} (expected 1-65535)")

    if "://" in host:
        scheme, _, remainder = host.partition("://")
        scheme = scheme.lower()
        if scheme not in ("http", "https"):
            raise ConfigError(
                f"Invalid TS_HTTP_SERVER_IP scheme: {scheme!r} (expected http/https)"
            )
        remainder = remainder.rstrip("/")
        if ":" in remainder.split("/")[0]:
            # Port already embedded in the host value; ignore separate port.
            return f"{scheme}://{remainder}"
        return f"{scheme}://{remainder}:{port}"

    return f"http://{host}:{port}"


def load_config() -> Config:
    load_dotenv()
    server_name = (
        os.getenv("TS_SERVER_NAME", "TeamSpeak Server").strip() or "TeamSpeak Server"
    )

    query_api_key = _get_required("TS_QUERY_API_KEY")
    host = _get_required("TS_HTTP_SERVER_IP")
    port = _get_required("TS_HTTP_SERVER_PORT")
    webhook_url = _get_required("DISCORD_WEBHOOK_URL").rstrip("/")
    config = Config(
        server_name=server_name,
        query_api_key=query_api_key,
        base_url=_build_base_url(host, port),
        webhook_url=webhook_url,
        message_id="",
    )
    if (
        os.getenv("DISCORD_MESSAGE_ID") is None
        or os.getenv("DISCORD_MESSAGE_ID").strip() == ""
    ):
        message_id = send_first_message(config)
    else:
        message_id = _get_required("DISCORD_MESSAGE_ID")
    config.message_id = message_id
    return config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="teamspeak-spy",
        description="Poll a TeamSpeak server and update a Discord webhook message with the online user count.",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Repeat every SECONDS seconds. Omit to run once.",
    )
    args = parser.parse_args(argv)
    if args.interval is not None and args.interval <= 0:
        parser.error("--interval must be a positive integer (seconds).")
    return args


def get_user_count(config: Config) -> int:
    try:
        response = requests.get(
            f"{config.base_url}/serverlist",
            headers={"x-api-key": config.query_api_key},
            timeout=config.timeout,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise SpyError(f"TeamSpeak query failed: {exc}") from exc
    except ValueError as exc:
        raise SpyError(f"TeamSpeak returned invalid JSON: {exc}") from exc

    try:
        body = data["body"]
        if not isinstance(body, list) or not body:
            raise KeyError("empty 'body' list")
        server = body[0]
        online = int(server["virtualserver_clientsonline"])
        query_online = int(server["virtualserver_queryclientsonline"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SpyError(f"Unexpected TeamSpeak response shape: {exc}") from exc

    return max(online - query_online, 0)


def send_first_message(config: Config) -> None:
    body = {
        "content": "",
        "embeds": [
            {
                "title": config.server_name,
                "description": (
                    "Settings things up, if this message persists, check console for errors."
                ),
            }
        ],
    }
    try:
        response = requests.post(
            f"{config.webhook_url}?wait=true",
            json=body,
            timeout=config.timeout,
        )
        response.raise_for_status()
        message_id = set_key(
            dotenv_path=find_dotenv(),
            key_to_set="DISCORD_MESSAGE_ID",
            value_to_set=str(response.json()["id"]),
        )
        return message_id
    except requests.RequestException as exc:
        raise SpyError(f"Discord webhook update failed: {exc}") from exc


def send_webhook_message(config: Config, user_count: int) -> None:
    cur_time = int(time.time())
    body = {
        "content": "",
        "embeds": [
            {
                "title": config.server_name,
                "description": (
                    f"Currently has **{user_count}** user{'s' if user_count > 1 else ''} online. {'🟢' if user_count > 0 else '🔴'}\n"
                    f"Last updated at: <t:{cur_time}>"
                ),
            }
        ],
    }
    try:
        response = requests.patch(
            f"{config.webhook_url}/messages/{config.message_id}",
            json=body,
            timeout=config.timeout,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        if response.status_code == 404:
            send_first_message(config)
        raise SpyError(f"Discord webhook update failed: {exc}") from exc


def run_once(config: Config) -> int:
    user_count = get_user_count(config)
    send_webhook_message(config, user_count)
    logger.info("Updated Discord message: %d users online.", user_count)
    return user_count


def run_forever(config: Config, interval: int) -> None:
    logger.info("Polling every %d seconds (Ctrl+C to stop).", interval)
    while True:
        try:
            run_once(config)
        except (SpyError, ConfigError) as exc:
            logger.error("%s", exc)
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Stopping on user request.")
            break


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("%s", exc)
        return 2
    try:
        if args.interval is None:
            run_once(config)
        else:
            run_forever(config, args.interval)
    except (SpyError, ConfigError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
