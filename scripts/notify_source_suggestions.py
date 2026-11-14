"""Privately collect suggestions, using the existing SMTP transport and recipient."""
from __future__ import annotations
import hashlib
import argparse
import os
import re
import sys
from email.message import EmailMessage
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from internships_project import email_alerts
from internships_project.public_safety import public_job_url

ENDPOINT='https://marketdesk-source-suggestions.theo-caruana.chatgpt.site'


def archive_suggestions(ids: list[str], session=None) -> int:
    if not ids or len(ids)>20 or any(not re.fullmatch(r'[a-f0-9]{64}',value) for value in ids):
        raise ValueError('Invalid suggestion identities')
    token=os.environ.get('SOURCE_SUGGESTIONS_TOKEN','').strip()
    if len(token)<32:
        raise ValueError('Suggestion collector is not configured')
    response=(session or requests.Session()).post(ENDPOINT+'/archive',json={'ids':ids},
        headers={'Authorization':'Bearer '+token},timeout=30,allow_redirects=False)
    response.raise_for_status()
    if response.json().get('success') is not True:
        raise RuntimeError('Suggestion archive failed')
    return len(ids)


def collect_and_notify(session=None) -> int:
    token=os.environ.get('SOURCE_SUGGESTIONS_TOKEN','').strip()
    if len(token)<32:
        raise ValueError('Suggestion collector is not configured')
    config=email_alerts._configuration(require_enabled=False)
    session=session or requests.Session()
    headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
    response=session.post(ENDPOINT+'/claim',json={},headers=headers,timeout=30,allow_redirects=False)
    response.raise_for_status()
    data=response.json()
    lease=data.get('lease')
    items=data.get('suggestions')
    if not isinstance(lease,str) or not re.fullmatch(r'[a-f0-9-]{36}',lease) or not isinstance(items,list) or len(items)>20:
        raise ValueError('Invalid suggestion batch')
    if not items:
        return 0
    for item in items:
        if not isinstance(item,dict) or set(item)!={'id','company','url','reason','created_at'}:
            raise ValueError('Invalid suggestion fields')
        if not isinstance(item['id'],str) or not re.fullmatch(r'[a-f0-9]{64}',item['id']):
            raise ValueError('Invalid suggestion identity')
        if any(not isinstance(item[k],str) or len(item[k])>limit for k,limit in [('company',80),('url',1000),('reason',600)]):
            raise ValueError('Invalid suggestion values')
        public_job_url(item['url'])
    message=EmailMessage()
    message['From']=config.sender
    message['To']=config.recipient
    message['Subject']=f'MarketDesk — {len(items)} nouvelle(s) source(s) proposée(s)'
    batch=hashlib.sha256('|'.join(sorted(item['id'] for item in items)).encode()).hexdigest()
    message['Message-ID']=f'<sources-{batch}@marketdesk.invalid>'
    lines=['Nouvelles sources proposées par les visiteurs de MarketDesk.',
           'Contenu fourni par les visiteurs, à vérifier avant toute intégration.','']
    for item in items:
        lines.extend([item['company'],item['url'],item['reason'] or 'Sans commentaire',''])
    message.set_content('\n'.join(lines))
    # SMTP accepts first; a failed send leaves the leased batch eligible for retry.
    email_alerts._send_message(config,message)
    ack=session.post(ENDPOINT+'/ack',json={'lease':lease,'ids':[item['id'] for item in items]},
                     headers=headers,timeout=30,allow_redirects=False)
    ack.raise_for_status()
    if ack.json().get('success') is not True:
        raise RuntimeError('Suggestion acknowledgement failed')
    return len(items)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',action='store_true')
    args=parser.parse_args()
    try:
        if args.archive:
            print(f'Source suggestions archived: {archive_suggestions(os.getenv("SOURCE_ARCHIVE_IDS","").split(","))}')
        else:
            print(f'Source suggestions delivered: {collect_and_notify()}')
    except Exception as exc:
        # SMTP responses, visitor text, addresses and authentication stay out of logs.
        print(f'Source suggestion delivery failed ({type(exc).__name__}); retained for retry.',file=sys.stderr)
        raise SystemExit(1)
