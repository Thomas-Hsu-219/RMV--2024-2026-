"""Manual refresh. Uses public metadata APIs, no account/API key required."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def get(url):
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'RMVMetadataLibrary/1.0 (public scholarly metadata)'})
            with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def crossref(filter_value):
    base='https://api.crossref.org/journals/1099-1654/works?'
    first=None; items=[]; cursor='*'
    while True:
        page=get(base+urllib.parse.urlencode({'filter':filter_value,'rows':1000,'cursor':cursor}))
        if first is None: first=page
        batch=page['message']['items']; items.extend(batch)
        if len(items)>=page['message']['total-results'] or not batch: break
        cursor=page['message']['next-cursor']; time.sleep(1)
    first['message']['items']=items
    return first

def epmc():
    base='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'
    cursor='*'; first=None; items=[]
    while True:
        page=get(base+urllib.parse.urlencode({'query':'(ISSN:1099-1654 OR ISSN:1052-9276) AND PUB_YEAR:[2024 TO 2026]','format':'json','resultType':'core','pageSize':1000,'cursorMark':cursor}))
        if first is None: first=page
        items.extend(page['resultList']['result'])
        if len(items)>=page['hitCount']: break
        cursor=page['nextCursorMark'];time.sleep(1)
    first['resultList']['result']=items
    return first

def main():
    p=argparse.ArgumentParser();p.add_argument('--cutoff',default=min(datetime.date.today().isoformat(),'2026-12-31'));p.add_argument('--source-root',type=Path,default=ROOT/'.refresh-sources');args=p.parse_args()
    date=datetime.date.fromisoformat(args.cutoff)
    if date.year not in (2024,2025,2026) or date>datetime.date.today(): raise ValueError('Cutoff must be a non-future date in 2024–2026')
    src=args.source_root.resolve()
    print('Fetching Crossref issue-year and publication-date inventories...',flush=True)
    save(src/'source_audit/crossref_issue_year.json',crossref('from-print-pub-date:2024-01-01,until-print-pub-date:2026-12-31'))
    save(src/'source_audit/crossref.json',crossref('from-pub-date:2024-01-01,until-pub-date:2026-12-31'))
    print('Fetching Europe PMC and original PubMed metadata...',flush=True)
    save(src/'pubmed/epmc_complete.json',epmc())
    subprocess.run([sys.executable,str(ROOT/'scripts/fetch_pubmed.py'),'--source-root',str(src)],check=True)
    shutil.copy2(ROOT/'scripts/verified-supplements/supplements.json',src/'source_audit/supplements.json')
    shutil.copy2(ROOT/'scripts/verified-supplements/title_supplements.json',src/'pubmed/title_supplements.json')
    subprocess.run([sys.executable,str(ROOT/'scripts/build_dataset.py'),'--source-root',str(src),'--cutoff',args.cutoff],check=True)
    print('Data rebuilt. Review quality-report.json, update documentation statistics/cutoff, recheck publisher coverage, then republish. No automatic publication was performed.')

if __name__=='__main__':main()
