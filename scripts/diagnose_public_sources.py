import sys,json,concurrent.futures
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from internships_project.internships import WORKDAY
def probe(company):
    host,tenant,site=WORKDAY[company]
    url=f'https://{host}/wday/cxs/{tenant}/{site}/jobs'
    result={'company':company}
    try:
        r=requests.post(url,json={'appliedFacets':{},'limit':20,'offset':0,'searchText':'Intern'},timeout=(8,25))
        result.update(status=r.status_code,type=r.headers.get('content-type'),bytes=len(r.content))
        try:
            data=r.json();result.update(total=data.get('total'),rows=len(data.get('jobPostings',[])), keys=list(data)[:8])
        except ValueError:
            import re
            title=re.search(r'<title>(.*?)</title>',r.text,re.S)
            result['html_title']=title[1][:150] if title else None; result['empty']=not bool(r.text.strip())
        return result
    except Exception as exc:return {**result,'error':type(exc).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for result in pool.map(probe,['BBVA','Deutsche Bank','Santander CIB','Euronext','MUFG','CIBC Capital Markets','Rothschild & Co','TD Securities','ING']):
        print(json.dumps(result),flush=True)
