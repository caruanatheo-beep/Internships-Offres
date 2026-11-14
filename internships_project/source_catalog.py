"""Public inventory generated from the same registry as the collectors."""
import re

from . import internships as jobs
from .public_safety import public_job_url


GROUPS = {
    'Société Générale Careers':'Société Générale',
    'Amundi · portail groupe':'Amundi',
    'BPCE Open Data':'BPCE / Natixis / BRED',
    'Lazard Student Careers':'Lazard', 'Lazard Professional Careers':'Lazard',
    'J.P. Morgan Careers':'J.P. Morgan', 'Goldman Sachs Campus Careers':'Goldman Sachs',
    'Schroders Careers':'Schroders', 'JobTeaser · sitemap':'JobTeaser',
    'Business France VIE':'Business France',
}
EXTRA_URLS = {
    'Société Générale Careers':'https://careers.societegenerale.com/',
    'Société Générale':'https://careers.societegenerale.com/',
    'Optiver':'https://optiver.com/working-at-optiver/career-opportunities/',
    'BNP Paribas VIE':'https://group.bnpparibas/emploi-carriere/toutes-offres-emploi/vie',
    'Business France VIE':'https://mon-vie-via.businessfrance.fr/offres',
    'Covéa Finance':'https://coveafinance-recrute.talent-soft.com/',
    'Comgest':'https://cm.comgest.com/fr/about-us/nos-collaborateurs/carrieres/stages',
    'BPCE Open Data':'https://recrutement.bpce.fr/offres-emploi',
    'JobTeaser · sitemap':'https://www.jobteaser.com/fr/job-offers',
    'Groupama AM':'https://www.groupama-am.com/fra/fr/intermediaire/carriere/groupama-asset-management-carriere',
    'AXA':"https://recrutement.axa.fr/recherche-d%27offres",
}
ASSET_MANAGERS = {
    'Sienna Investment Managers','Sycomore Asset Management','Point72','Qube Research & Technologies',
    '21shares','WisdomTree','Amundi','Covéa Finance','Comgest','DNCA','Candriam','Groupama AM',
    'Schroders','La Française','Ofi Invest','Tikehau Capital','CFM',
}
TRADING = {'Jane Street','IMC Trading','Flow Traders','Da Vinci','Optiver','Statkraft','Marex','Kepler Cheuvreux'}
OTHER = {'Finance Active','Banque de France','Business France','JobTeaser','AXA','Euronext'}


def public_source_catalog() -> list[dict]:
    urls = dict(jobs.CAREER_PORTALS)
    urls.update({company:config[0] for company,config in jobs.CAREER_LISTINGS.items()})
    urls.update({company:f'https://{host}/en-US/{site}' for company,(host,tenant,site) in jobs.WORKDAY.items()})
    urls.update({name:f'{host}/hcmUI/CandidateExperience/en/sites/{site}/jobs'
                 for name,(host,site,company) in jobs.ORACLE_CAREER_BOARDS.items()})
    for registry,base in ((jobs.SMARTRECRUITERS,'https://careers.smartrecruiters.com/'),
                          (jobs.GREENHOUSE,'https://job-boards.greenhouse.io/'),
                          (jobs.LEVER,'https://jobs.lever.co/'),(jobs.ASHBY,'https://jobs.ashbyhq.com/')):
        urls.update({company:base+slug for slug,company in registry.items()})
    urls.update(EXTRA_URLS)
    groups = {}
    for name,_,_ in jobs._opportunity_source_tasks():
        url = public_job_url(urls[name])
        group = 'BNP Paribas' if name.startswith('BNP Paribas') else GROUPS.get(name,name)
        if group not in groups:
            category=('Gestion d’actifs' if group in ASSET_MANAGERS else
                      'Courtage & trading' if group in TRADING else
                      'Autres sources' if group in OTHER else 'Banques & services titres')
            groups[group]={'name':group,'category':category,'url':url,'feeds':[]}
        groups[group]['feeds'].append({'name':name,'url':url})
        if name==group:
            groups[group]['url']=url
    return sorted(groups.values(),key=lambda source:source['name'].casefold())


def validate_source_catalog(data: dict) -> None:
    if set(data) != {'updated','sources','request_endpoint'} or not isinstance(data['updated'],str) or not isinstance(data['sources'],list):
        raise ValueError('Invalid public source catalog')
    if data['request_endpoint'] not in ('','https://marketdesk-source-suggestions.theo-caruana.chatgpt.site/suggestions'):
        raise ValueError('Invalid source request endpoint')
    for source in data['sources']:
        if set(source) != {'name','category','url','feeds','logo'}:
            raise ValueError('Unexpected source catalog field')
        if any(not isinstance(source[key],str) or len(source[key])>500 for key in ('name','category','url','logo')):
            raise ValueError('Invalid source catalog value')
        public_job_url(source['url'])
        if source['logo'] and not re.fullmatch(r'logos/[A-Za-z0-9._-]+\.png',source['logo']):
            raise ValueError('Invalid public source logo')
        if not isinstance(source['feeds'],list) or not source['feeds']:
            raise ValueError('Missing source feeds')
        for feed in source['feeds']:
            if set(feed) != {'name','url'} or not isinstance(feed['name'],str) or len(feed['name'])>150 or not isinstance(feed['url'],str) or len(feed['url'])>500:
                raise ValueError('Invalid public source feed')
            public_job_url(feed['url'])
