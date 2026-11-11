"""Public-source repairs: ordinary virtual browser and Altays pagination."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from internships_project import internships as jobs


@pytest.mark.parametrize("environment,headless", [
    ({}, True), ({"DISPLAY": ":99"}, True),
    ({"GITHUB_ACTIONS": "true", "DISPLAY": ":99"}, False),
])
def test_bnp_uses_virtual_display_only_on_github(monkeypatch, environment, headless):
    monkeypatch.setattr(jobs, "os", SimpleNamespace(name="posix", getenv=environment.get))
    browser = Mock(return_value=[])
    monkeypatch.setattr(jobs, "_bnp_group_jobs_browser", browser)
    assert jobs._bnp_group_jobs("BNP Paribas", "https://group.bnpparibas/listing") == []
    browser.assert_called_once_with("BNP Paribas", "https://group.bnpparibas/listing", headless=headless)


def test_oddo_reads_ajax_pages_and_official_pdfs(monkeypatch):
    import pypdf
    description = "Localisation : Paris Type de contrat : Stage Date de publication : 10/11/2026"
    monkeypatch.setattr(pypdf, "PdfReader", lambda stream: SimpleNamespace(
        pages=[SimpleNamespace(extract_text=lambda: description)]))
    detail = "https://recrutement.altays-progiciels.com/oddo/fr/offres/stage-sales-123.pdf"
    seen_pages = []

    def get(url, **kwargs):
        if url == jobs.ODDO_ALTAYS_LISTING:
            text = '<div style="display:none">An error has occurred</div>'
        elif url == detail:
            return SimpleNamespace(content=b"synthetic PDF", raise_for_status=lambda: None)
        else:
            assert url == "https://recrutement.altays-progiciels.com/oddo/fr/offres.html"
            number = kwargs["params"]["page"]
            seen_pages.append(number)
            text = {1: '<a href="/oddo/fr/offres/stage-sales-123.html?page=1">Stage Sales</a>'
                       '<a href="https://evil.invalid/oddo/fr/offres/stage-sales-456.html">Stage Sales</a>',
                    2: '<a href="/oddo/fr/offres/comptable-222.html">Comptable CDI</a>',
                    3: ''}[number]
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    monkeypatch.setattr(jobs.requests, "get", get)
    found = jobs._oddo_jobs()
    assert seen_pages == [1, 2, 3]
    assert len(found) == 1
    assert (found[0].url, found[0].location, found[0].published) == (detail, "Paris", "2026-11-10")


def test_oddo_does_not_accept_repeating_or_broken_listing(monkeypatch):
    monkeypatch.setattr(jobs.requests, "get", lambda *a, **kw: SimpleNamespace(
        text='<a href="/oddo/fr/offres/stage-sales-123.html">Stage Sales</a>',
        raise_for_status=lambda: None))
    with pytest.raises(ValueError, match="pagination Altays répétée"):
        jobs._oddo_jobs()
