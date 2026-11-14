import pytest

from internships_project import internships as jobs
from internships_project.source_catalog import public_source_catalog, validate_source_catalog


def test_catalog_exactly_covers_active_collectors_and_groups_related_portals():
    catalog=public_source_catalog()
    feeds=[feed['name'] for source in catalog for feed in source['feeds']]
    assert set(feeds)=={name for name,_,_ in jobs._opportunity_source_tasks()}
    assert len(feeds)==len(set(feeds))
    assert len(catalog)<len(feeds)
    assert {'Commerzbank','Standard Chartered','Candriam','BNY'} <= {source['name'] for source in catalog}
    assert not any('Palatine' in source['name'] or source['name']=='TP ICAP' for source in catalog)
    bnp=next(source for source in catalog if source['name']=='BNP Paribas')
    assert len(bnp['feeds'])>=4
    assert next(source for source in catalog if source['name']=='Candriam')['category']=='Gestion d’actifs'


@pytest.mark.parametrize('endpoint',['https://evil.invalid/suggestions','https://user@example.com/suggestions',None])
def test_catalog_rejects_unknown_receivers_and_email_addresses(endpoint):
    source={**public_source_catalog()[0],'logo':''}
    with pytest.raises(ValueError):
        validate_source_catalog({'updated':'2026-11-14','sources':[source],'request_endpoint':endpoint})


def test_catalog_rejects_extra_private_fields_and_unsafe_links():
    source={**public_source_catalog()[0],'logo':''}
    for patch in ({'password':'private'},{'url':'http://localhost/'},{'logo':'logos/../../private.png'}):
        with pytest.raises(ValueError):
            validate_source_catalog({'updated':'2026-11-14','sources':[{**source,**patch}],'request_endpoint':''})
