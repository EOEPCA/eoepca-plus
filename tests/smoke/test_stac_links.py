"""Smoke tests for STAC API link integrity.

Catches regressions where internal ports (e.g. :9443) leak into response links.
"""

import os
import re

import httpx
import pytest

EOAPI = os.environ.get("EOAPI", "eoapi.rke2.deploybox.co.uk")
STAC_URL = f"https://{EOAPI}/stac/"

# Matches URLs containing a non-standard port (anything other than :443 or :80)
NON_STANDARD_PORT = re.compile(r"https?://[^/]+:(?!443\b|80\b)\d+")


@pytest.fixture(scope="module")
def stac_landing_page():
    resp = httpx.get(STAC_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def test_landing_page_has_links(stac_landing_page):
    links = stac_landing_page.get("links", [])
    assert links, "Landing page should contain at least one link"


def test_no_internal_ports_in_links(stac_landing_page):
    bad = []
    for link in stac_landing_page.get("links", []):
        href = link.get("href", "")
        if NON_STANDARD_PORT.search(href):
            bad.append(href)
    assert not bad, f"Links contain non-standard ports: {bad}"
