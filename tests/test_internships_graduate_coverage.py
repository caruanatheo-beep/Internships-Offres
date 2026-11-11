"""Graduate audit regressions, using public-shaped synthetic catalogues."""
import json
from types import SimpleNamespace

import pytest

from internships_project import internships as jobs


@pytest.mark.parametrize("title,employment,expected", [
    ("2027 MUFG UK Summer Analyst Programme: Global Client Sales", "", "Stage"),
    ("Global Markets Summer Associate Programme 2027", "Full time", "Stage"),
    ("2027 MUFG UK Analyst Programme: Global Markets", "", "Graduate"),
    ("Global Markets Graduate Programme", "Permanent contract", "Graduate"),
    ("Graduate Quantitative Researcher", "CDI", "Graduate"),
    ("Global Markets Graduates Programme", "CDD", "Graduate"),
    ("Markets - Sales and Trading, Full Time Analyst, London, 2027", "Permanent", "Graduate"),
    ("Markets, Quantitative Analysis, Full-Time Associate, London, 2027", "", "Graduate"),
    ("International Talent Programme - Financial Markets", "", "Graduate"),
    ("Traineeprogramm Capital Markets", "", "Graduate"),
    ("New Analyst - Equities", "Permanent", "Graduate"),
    ("Senior Sales", "Permanent contract", None),
    ("Full Time Analyst - Global Markets", "", None),
    ("Sales Intern", "Permanent contract", None),
    ("Graduate Programme Markets", "Apprenticeship", None),
    ("Stage Sales", "Alternance", None),
])
def test_programme_contracts(title, employment, expected):
    assert jobs._kind(title, employment) == expected


@pytest.mark.parametrize("city", ["Paris", "London", "Frankfurt", "Amsterdam", "Zurich",
                                   "Geneva", "Luxembourg", "Madrid", "Milan", "Dublin",
                                   "Stockholm", "Copenhagen"])
def test_european_cities_do_not_exclude_graduates(city):
    job = jobs._opportunity("Global Markets Graduate Programme", "Bank", city, "CDI",
                            "https://jobs.smartrecruiters.com/bank/123", "")
    assert job and job.kind == "Graduate"
    assert jobs.matching_opportunities([job], category="Graduate") == [job]


@pytest.mark.parametrize("title", [
    "Graduate Middle Office - Global Markets", "Graduate Corporate Finance",
    "Asset Management, Controls Governance & Testing | New Analyst",
    "Graduate Quantitative Researcher - Expression of Interest",
    "Graduate Trading Talent Pool", "Graduate Real Estate Fund Management",
])
def test_non_desk_and_interest_only_roles_stay_excluded(title):
    assert not jobs._opportunity(title, "Bank", "London", "",
                                 "https://jobs.smartrecruiters.com/bank/123", "")


def test_greenhouse_eu_is_trusted_but_not_a_lookalike(monkeypatch):
    url = "https://job-boards.eu.greenhouse.io/imc/jobs/123"
    monkeypatch.setattr(jobs.requests, "get", lambda *a, **kw: SimpleNamespace(
        json=lambda: {"jobs": [{"title": "Graduate Quantitative Researcher",
            "location": {"name": "Amsterdam"}, "absolute_url": url, "content": "Quantitative research"}]},
        raise_for_status=lambda: None))
    assert [j.url for j in jobs._greenhouse_jobs("imc", "IMC Trading")] == [url]
    assert not jobs.is_trusted_offer_url(url.replace("greenhouse.io", "greenhouse.io.evil.invalid"))


@pytest.mark.parametrize("second_page_fails", [False, True])
def test_optiver_new_catalogue_pagination(monkeypatch, second_page_fails):
    rows = [{"title": "Senior Trader", "location": "Amsterdam", "experience": "Experienced",
             "href": f"/join-us/jobs/trading/amsterdam/senior-{i}/"} for i in range(16)]
    graduate = {"title": "Graduate Quantitative Researcher (2027 Start)", "location": "Amsterdam",
                "experience": "Graduate", "href": "/join-us/jobs/quant/amsterdam/graduate/"}
    if second_page_fails:
        rows[0] = graduate
    offsets = []
    def get(url, **kwargs):
        if url.endswith('/en/api/v1/jobs'):
            offset = kwargs['params']['from']; offsets.append(offset)
            if offset and second_page_fails:
                raise jobs.requests.ReadTimeout()
            payload = {'items': rows if offset == 0 else [graduate], 'totalCount': 17}
            return SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None)
        assert url == 'https://www.optiver.com' + graduate['href']
        detail = {'@type':'JobPosting','datePosted':'2026-11-10',
                  'description':'Quantitative research on our trading floor. Start date: September 2027.'}
        return SimpleNamespace(text='<script type="application/ld+json">'+json.dumps(detail)+'</script>',
                               raise_for_status=lambda: None)
    monkeypatch.setattr(jobs.requests, 'get', get)
    monkeypatch.setattr(jobs, '_cached_detail', lambda job: None)
    if second_page_fails:
        with pytest.raises(jobs._PartialSourceError) as failure:
            jobs._optiver_jobs()
        found = failure.value.jobs
        assert failure.value.preserve_cached
    else:
        found = jobs._optiver_jobs()
    assert offsets == ([0,16,16] if second_page_fails else [0,16])
    assert len(found) == 1 and found[0].kind == 'Graduate' and found[0].location == 'Amsterdam'
