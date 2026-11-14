"""Anonymous source suggestions: browser checks with a simulated storage receiver."""
import pytest
from playwright.sync_api import expect
from tests.test_pages_filters import browser, ROOT, BASE

ENDPOINT = 'https://marketdesk-source-suggestions.source-suggestions.workers.dev/suggestions'


@pytest.fixture
def sources_screen(browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    calls, errors = [], []
    state = {'enabled': True, 'success': True, 'proposals': []}
    page.on('pageerror', lambda error: errors.append(str(error)))
    def route(request):
        if request.request.url == ENDPOINT:
            if request.request.method=='GET':
                request.fulfill(json={'suggestions':state['proposals']})
                return
            calls.append(request.request.post_data_json)
            if state['success']:
                state['proposals'].append(calls[-1])
            request.fulfill(json={'success': state['success']})
            return
        name = request.request.url.removeprefix(BASE).split('?')[0] or 'index.html'
        if name == 'sources.json':
            request.fulfill(json={'request_endpoint': ENDPOINT if state['enabled'] else '', 'sources': [
                dict(name='BNP Paribas', category='Banques & services titres', url='https://example.com/bnp', logo='',
                     feeds=[dict(name='BNP France', url='https://example.com/fr'), dict(name='BNP Monde', url='https://example.com/global')]),
                dict(name='Candriam', category='Gestion d’actifs', url='https://example.com/candriam', logo='',
                     feeds=[dict(name='Candriam', url='https://example.com/candriam')])]})
        elif name == 'offers.json':
            request.fulfill(json={'offers': [], 'sources': {}, 'updated': ''})
        elif name in {'index.html', 'site.css', 'app.js', 'sources.js', 'marketdesk-icon.svg'}:
            body = (ROOT / name).read_text(encoding='utf-8')
            if name == 'index.html':
                body = body.replace("connect-src 'self';", "connect-src 'self' https://marketdesk-source-suggestions.source-suggestions.workers.dev;")
            mime = {'html': 'text/html', 'css': 'text/css', 'js': 'application/javascript', 'svg': 'image/svg+xml'}
            request.fulfill(body=body, content_type=mime[name.rsplit('.', 1)[1]])
        else:
            request.abort()
    page.route('**/*', route)
    page.goto(BASE + '#sources', wait_until='networkidle')
    page.locator('.source-card').first.wait_for()
    yield page, calls, state
    assert not errors, errors
    page.close()


def fill_suggestion(page):
    page.locator('#source-name').fill('Nouvelle banque')
    page.locator('#source-url').fill('https://careers.example.com/jobs')
    page.locator('#source-reason').fill('Des stages Sales à Paris')


def test_catalog_navigation_search_and_mobile(sources_screen):
    page, calls, _ = sources_screen
    assert page.locator('.source-card').count() == 2
    page.locator('.source-card details').first.locator('summary').click()
    assert page.locator('.source-card details a:visible').count() == 2
    page.locator('[data-category="Banques & services titres"]').click()
    assert page.locator('.source-card h3').inner_text() == 'BNP Paribas'
    page.locator('[data-category=""]').click()
    page.locator('#source-search').fill('candriam')
    assert page.locator('.source-card').count() == 1
    page.locator('#nav-offers').click()
    expect(page.locator('#offers-view')).to_be_visible()
    page.locator('#nav-sources').click()
    expect(page.locator('#sources-view')).to_be_visible()
    assert page.locator('#source-search').input_value() == 'candriam'
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not calls


def test_anonymous_submission_success(sources_screen):
    page, calls, _ = sources_screen
    fill_suggestion(page)
    page.locator('#source-submit').click()
    page.get_by_text('Ta suggestion a été enregistrée. Merci !', exact=True).wait_for()
    assert len(calls) == 1
    assert calls[0]['company'] == 'Nouvelle banque'
    assert calls[0]['url'] == 'https://careers.example.com/jobs'
    assert not any(key in calls[0] for key in ['email', 'password', 'token'])
    assert page.locator('#source-name').input_value() == ''
    expect(page.locator('#proposed-list h3')).to_have_text('Nouvelle banque')


def test_failed_submission_preserves_fields_and_can_retry(sources_screen):
    page, calls, state = sources_screen
    state['success'] = False
    fill_suggestion(page)
    page.locator('#source-submit').click()
    page.locator('#source-request-status.is-error').wait_for()
    assert page.locator('#source-name').input_value() == 'Nouvelle banque'
    assert page.locator('#source-submit').is_enabled()
    state['success'] = True
    page.locator('#source-submit').click()
    page.get_by_text('Ta suggestion a été enregistrée. Merci !', exact=True).wait_for()
    assert len(calls) == 2


def test_unconfigured_receiver_disables_submission(sources_screen):
    page, calls, state = sources_screen
    state['enabled'] = False
    page.reload(wait_until='networkidle')
    assert page.locator('#source-name').is_disabled()
    assert page.locator('#source-submit').is_disabled()
    assert not calls
