from types import SimpleNamespace
import pytest
from scripts import notify_source_suggestions as notify


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('SOURCE_SUGGESTIONS_TOKEN','unit-test-collector-token-not-a-real-secret')
    monkeypatch.setattr(notify.email_alerts,'_configuration',lambda **kw:SimpleNamespace(sender='sender@example.test',recipient='owner@example.test'))
    sent=[]
    monkeypatch.setattr(notify.email_alerts,'_send_message',lambda config,message:sent.append(message))
    batch={'lease':'a'*36,'suggestions':[{'id':'b'*64,'company':'Banque Test','url':'https://example.com/careers','reason':'Stages Sales','created_at':1}]}
    calls=[]
    class Response:
        def __init__(self,data): self.data=data
        def raise_for_status(self): pass
        def json(self): return self.data
    class Session:
        def post(self,url,**kwargs):
            calls.append((url,kwargs))
            return Response(batch if url.endswith('/claim') else {'success':True})
    return Session(),batch,calls,sent


def test_existing_smtp_is_reused_and_ack_follows_delivery(setup):
    session,batch,calls,sent=setup
    assert notify.collect_and_notify(session)==1
    assert len(sent)==1
    assert sent[0]['To']=='owner@example.test'
    assert 'Stages Sales' in sent[0].get_content()
    assert calls[1][1]['json']['ids']==['b'*64]
    assert all(call[1]['allow_redirects'] is False for call in calls)


def test_smtp_failure_does_not_acknowledge_suggestions(setup,monkeypatch):
    session,_,calls,_=setup
    def fail(*args):raise RuntimeError('Delivery failed')
    monkeypatch.setattr(notify.email_alerts,'_send_message',fail)
    with pytest.raises(RuntimeError):notify.collect_and_notify(session)
    assert len(calls)==1


def test_empty_queue_sends_nothing(setup):
    session,batch,calls,sent=setup
    batch['suggestions']=[]
    assert notify.collect_and_notify(session)==0
    assert not sent and len(calls)==1


def test_invalid_or_contaminated_queue_sends_nothing(setup):
    session,batch,calls,sent=setup
    batch['suggestions'][0]['url']='https://example.com/?token=private'
    with pytest.raises(ValueError):notify.collect_and_notify(session)
    assert not sent and len(calls)==1


def test_missing_collector_secret_fails_before_network(setup,monkeypatch):
    session,_,calls,_=setup
    monkeypatch.delenv('SOURCE_SUGGESTIONS_TOKEN')
    with pytest.raises(ValueError):notify.collect_and_notify(session)
    assert not calls


def test_only_valid_identities_can_be_archived(setup):
    session,_,calls,_=setup
    with pytest.raises(ValueError):notify.archive_suggestions(['bad'],session)
    assert not calls
    assert notify.archive_suggestions(['b'*64],session)==1
    assert calls[0][0].endswith('/archive')
