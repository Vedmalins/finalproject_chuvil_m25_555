from __future__ import annotations

from typing import Any

import valutatrade_hub.parser_service.api_clients as api_clients


class DummyResponse:
    def __init__(self, status_code: int, url: str, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.url = url
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_exchange_rate_client_builds_v6_url_and_parses(monkeypatch) -> None:
    called = {}

    def fake_get(url: str, params: dict | None = None, timeout: int | None = None):
        called["url"] = url
        called["params"] = params
        called["timeout"] = timeout
        payload = {
            "result": "success",
            "base_code": "USD",
            "conversion_rates": {"USD": 1.0, "EUR": 0.92, "RUB": 98.45},
        }
        return DummyResponse(200, url, payload)

    monkeypatch.setattr(api_clients, "EXCHANGERATE_API_KEY", "test-key")
    monkeypatch.setattr(api_clients.requests, "get", fake_get)

    client = api_clients.ExchangeRateClient()
    data = client.fetch_rates()

    assert called["url"].endswith("/test-key/latest/USD")
    assert data["base"] == "USD"
    assert data["rates"]["EUR"] == 0.92
    assert data["rates"]["RUB"] == 98.45


def test_exchange_rate_client_missing_key_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(api_clients, "EXCHANGERATE_API_KEY", "")
    client = api_clients.ExchangeRateClient()
    assert client.fetch_rates() == {}


def test_coingecko_client_maps_ids_to_codes(monkeypatch) -> None:
    def fake_get(url: str, params: dict | None = None, timeout: int | None = None):
        payload = {
            "bitcoin": {"usd": 59337.21},
            "ethereum": {"usd": 3720.0},
            "solana": {"usd": 145.12},
        }
        return DummyResponse(200, url, payload)

    monkeypatch.setattr(api_clients.requests, "get", fake_get)
    monkeypatch.setattr(
        api_clients,
        "CRYPTO_ID_MAP",
        {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"},
    )

    client = api_clients.CoinGeckoClient()
    data = client.fetch_rates()

    assert data["BTC"]["usd"] == 59337.21
    assert data["ETH"]["usd"] == 3720.0
    assert data["SOL"]["usd"] == 145.12
