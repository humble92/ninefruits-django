"""Client address behind reverse proxies (``ninefruits.core.http.client_ip``)."""

from __future__ import annotations

import pytest
from django.test import RequestFactory, override_settings

from ninefruits.core.http import client_ip


def _request(forwarded: str | None = None, remote: str = "10.0.0.1") -> object:
    extra = {"REMOTE_ADDR": remote}
    if forwarded is not None:
        extra["HTTP_X_FORWARDED_FOR"] = forwarded
    return RequestFactory().get("/", **extra)


@override_settings(TRUSTED_PROXY_COUNT=0)
def test_without_trusted_proxies_the_forwarded_header_is_ignored() -> None:
    assert client_ip(_request("203.0.113.9")) == "10.0.0.1"


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_one_proxy_takes_the_rightmost_entry() -> None:
    # The client prepended a forged address; only what the proxy appended counts.
    assert client_ip(_request("198.51.100.66, 203.0.113.9")) == "203.0.113.9"


@override_settings(TRUSTED_PROXY_COUNT=2)
def test_two_proxies_count_from_the_right() -> None:
    assert client_ip(_request("198.51.100.66, 203.0.113.9, 10.1.1.1")) == "203.0.113.9"


@pytest.mark.parametrize("forwarded", ["", "not-an-ip", "2001:db8::1, garbage"])
@override_settings(TRUSTED_PROXY_COUNT=1)
def test_missing_or_malformed_header_falls_back_to_remote_addr(forwarded: str) -> None:
    assert client_ip(_request(forwarded)) == "10.0.0.1"


@override_settings(TRUSTED_PROXY_COUNT=3)
def test_header_shorter_than_the_proxy_chain_falls_back() -> None:
    assert client_ip(_request("203.0.113.9")) == "10.0.0.1"


@override_settings(TRUSTED_PROXY_COUNT=1)
def test_ipv6_is_normalized() -> None:
    assert client_ip(_request("2001:DB8:0:0::1")) == "2001:db8::1"
