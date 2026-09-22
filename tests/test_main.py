from unittest.mock import MagicMock, patch

import pytest

from teamspeak_spy.main import (
    Config,
    ConfigError,
    SpyError,
    _build_base_url,
    get_user_count,
    load_config,
    parse_args,
)


def _config(**overrides):
    base = {
        "server_name": "Test",
        "query_api_key": "key",
        "base_url": "http://127.0.0.1:10080",
        "webhook_url": "https://discord.com/api/webhooks/x",
        "message_id": "123",
    }
    base.update(overrides)
    return Config(**base)


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_build_base_url_plain():
    assert _build_base_url("127.0.0.1", "10080") == "http://127.0.0.1:10080"


def test_build_base_url_with_scheme():
    assert (
        _build_base_url("https://example.com/", "10080") == "https://example.com:10080"
    )


def test_build_base_url_invalid_port():
    with pytest.raises(ConfigError):
        _build_base_url("127.0.0.1", "notaport")


def test_get_user_count_subtracts_query_clients():
    payload = {
        "body": [
            {
                "virtualserver_clientsonline": "5",
                "virtualserver_queryclientsonline": "2",
            }
        ]
    }
    with patch("teamspeak_spy.main.requests.get", return_value=_mock_response(payload)):
        assert get_user_count(_config()) == 3


def test_get_user_count_empty_body():
    with patch(
        "teamspeak_spy.main.requests.get", return_value=_mock_response({"body": []})
    ):
        with pytest.raises(SpyError):
            get_user_count(_config())


def test_load_config_missing_key(monkeypatch):
    monkeypatch.setattr("teamspeak_spy.main.load_dotenv", lambda: None)
    for var in (
        "TS_QUERY_API_KEY",
        "TS_HTTP_SERVER_IP",
        "TS_HTTP_SERVER_PORT",
        "DISCORD_WEBHOOK_URL",
        "DISCORD_WEBOOK_URL",
        "DISCORD_MESSAGE_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TS_HTTP_SERVER_IP", "127.0.0.1")
    monkeypatch.setenv("TS_HTTP_SERVER_PORT", "10080")
    with pytest.raises(ConfigError):
        load_config()


def test_load_config_legacy_webhook(monkeypatch):
    monkeypatch.setattr("teamspeak_spy.main.load_dotenv", lambda: None)
    monkeypatch.setenv("TS_QUERY_API_KEY", "key")
    monkeypatch.setenv("TS_HTTP_SERVER_IP", "127.0.0.1")
    monkeypatch.setenv("TS_HTTP_SERVER_PORT", "10080")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("DISCORD_WEBOOK_URL", "https://discord.com/api/webhooks/legacy")
    monkeypatch.setenv("DISCORD_MESSAGE_ID", "123")
    assert load_config().webhook_url == "https://discord.com/api/webhooks/legacy"


def test_parse_args_interval_validation():
    assert parse_args([]).interval is None
    assert parse_args(["--interval", "60"]).interval == 60
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0"])
