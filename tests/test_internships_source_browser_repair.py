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


@pytest.mark.parametrize("shell_unavailable", [False, True])
def test_oddo_reads_ajax_pages_and_official_pdfs(monkeypatch, shell_unavailable):
    import pypdf
    description = "Localisation : Paris Type de contrat : Stage Date de publication : 10/11/2026"
    monkeypatch.setattr(pypdf, "PdfReader", lambda stream: SimpleNamespace(
        pages=[SimpleNamespace(extract_text=lambda: description)]))
    detail = "https://recrutement.altays-progiciels.com/oddo/fr/offres/stage-sales-123.pdf"
    seen_pages = []

    def get(url, **kwargs):
        if url == jobs.ODDO_ALTAYS_LISTING:
            if shell_unavailable:
                raise jobs.requests.ConnectTimeout("legacy search unavailable")
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


def test_cib_retries_unreachable_archives_in_virtual_browser(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setattr(jobs.requests, "get", Mock(side_effect=jobs.requests.ReadTimeout()))
    render = Mock(return_value='<a href="/jobs/trading-intern/">Trading intern</a>')
    monkeypatch.setattr(jobs, "_render_public_career_page", render)
    monkeypatch.setattr(jobs, "_career_detail", lambda url, company, title: jobs._opportunity(
        title, company, "Paris", "Stage", url, ""))
    found = jobs._bnp_cib_jobs()
    assert len(found) == 1
    assert render.call_count == 10


def test_cib_failed_details_are_not_reported_as_empty_success(monkeypatch):
    monkeypatch.setattr(jobs.requests, "get", lambda *a, **kw: SimpleNamespace(
        text='<a href="/jobs/trading-intern/">Trading intern</a>', raise_for_status=lambda: None))
    monkeypatch.setattr(jobs, "_career_detail", Mock(side_effect=jobs.requests.ReadTimeout()))
    monkeypatch.delenv("DISPLAY", raising=False)
    with pytest.raises(jobs._PartialSourceError) as error:
        jobs._bnp_cib_jobs()
    assert error.value.failed_urls == {'https://careers.cib.bnpparibas/jobs/trading-intern/'}
