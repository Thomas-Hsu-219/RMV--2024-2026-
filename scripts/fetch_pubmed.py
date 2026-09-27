import json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source-root',required=True,type=Path)
args=parser.parse_args()
ROOT=args.source_root/'pubmed'
ROOT.mkdir(parents=True,exist_ok=True)
BASE='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
QUERIES=[
 '("1099-1654"[ISSN] OR "1052-9276"[ISSN]) AND ("2024/01/01"[Date - Publication] : "2026/12/31"[Date - Publication])',
 '("Reviews in Medical Virology"[Journal]) AND ("2024/01/01"[Date - Publication] : "2026/12/31"[Date - Publication])',
]
requests=[]
def get(endpoint, params):
    url=BASE+endpoint+'?'+urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            time.sleep(0.45)
            req=urllib.request.Request(url,headers={'User-Agent':'RMVMetadataArchive/1.0 (academic bibliography)'})
            with urllib.request.urlopen(req,timeout=120) as f:
                data=f.read()
            requests.append({'url':url,'fetched_at':datetime.now(timezone.utc).isoformat(),'bytes':len(data)})
            return data
        except Exception as exc:
            print('retry',attempt+1,endpoint,str(exc),flush=True)
            if attempt==5: raise
            time.sleep(2**attempt)

initial=json.loads((ROOT/'epmc_complete.json').read_text('utf-8'))['resultList']['result']
initial_ids={str(x.get('pmid') or x.get('id')) for x in initial if x.get('source')=='MED'}
ids=set(initial_ids)
search_results=[]
for i,q in enumerate(QUERIES,1):
    data=get('esearch.fcgi',{'db':'pubmed','term':q,'retmode':'json','retmax':'10000'})
    (ROOT/f'search_{i}.json').write_bytes(data)
    result=json.loads(data)
    search_results.append({'query':q,'count':result['esearchresult']['count'],'ids':result['esearchresult']['idlist']})
    ids.update(result['esearchresult']['idlist'])
print('Initial:',len(initial_ids),'Total:',len(ids),'Extra:',len(ids-initial_ids),flush=True)
allroot=ET.Element('PubmedArticleSet')
sorted_ids=sorted(ids,key=int)
for i in range(0,len(sorted_ids),75):
    group=sorted_ids[i:i+75]
    raw=get('efetch.fcgi',{'db':'pubmed','id':','.join(group),'retmode':'xml'})
    (ROOT/f'batch_{i//75+1}.xml').write_bytes(raw)
    root=ET.fromstring(raw)
    for el in root: allroot.append(el)
    print('Fetched',i+len(group),'of',len(sorted_ids),flush=True)
ET.ElementTree(allroot).write(ROOT/'pubmed.xml',encoding='utf-8',xml_declaration=True)

def txt(el):
    return ''.join(el.itertext()).strip() if el is not None else ''
def date(el):
    if el is None: return None
    return {child.tag:txt(child) for child in el}
records={}
doi_missing=[]
for article in allroot.findall('PubmedArticle'):
    cit=article.find('MedlineCitation')
    a=cit.find('Article')
    pmid=txt(cit.find('PMID'))
    doi=next((txt(e).lower() for e in article.findall('PubmedData/ArticleIdList/ArticleId') if e.get('IdType')=='doi'),'')
    if not doi:
        doi=next((txt(e).lower() for e in a.findall('ELocationID') if e.get('EIdType')=='doi'),'')
    sections=[]
    for e in a.findall('Abstract/AbstractText'):
        sections.append({'label':e.get('Label'),'category':e.get('NlmCategory'),'text':txt(e)})
    abstract='\n\n'.join((s['label']+': ' if s['label'] else '')+s['text'] for s in sections)
    rec={
        'pmid':pmid,'doi':doi,'title':txt(a.find('ArticleTitle')),
        'abstract':abstract,'abstract_sections':sections,
        'author_keywords':[txt(e) for e in cit.findall('KeywordList/Keyword')],
        'keyword_list_owners':[e.get('Owner') for e in cit.findall('KeywordList')],
        'publication_types':[txt(e) for e in a.findall('PublicationTypeList/PublicationType')],
        'publication_date_print':date(a.find('Journal/JournalIssue/PubDate')),
        'publication_date_electronic':[date(e) for e in a.findall('ArticleDate') if e.get('DateType')=='Electronic'],
        'copyright_statement':txt(a.find('Abstract/CopyrightInformation')),
        'journal':txt(a.find('Journal/Title')),
        'volume':txt(a.find('Journal/JournalIssue/Volume')),
        'issue':txt(a.find('Journal/JournalIssue/Issue')),
        'source_url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
        'additional_to_initial_europepmc':pmid not in initial_ids,
    }
    if doi: records[doi]=rec
    else: doi_missing.append(rec)
(ROOT/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf-8')
(ROOT/'doi_missing.json').write_text(json.dumps(doi_missing,ensure_ascii=False,indent=2),'utf-8')
summary={
    'retrieved_at':datetime.now(timezone.utc).isoformat(),
    'queries':search_results,
    'initial_med_pmids':len(initial_ids),'union_pmids':len(ids),
    'additional_pmids':sorted(ids-initial_ids,key=int),
    'records_by_doi':len(records),'records_without_doi':len(doi_missing),
    'missing_abstract':sum(not x['abstract'] for x in records.values()),
    'missing_author_keywords':sum(not x['author_keywords'] for x in records.values()),
    'missing_title':sum(not x['title'] for x in records.values()),
    'requests':requests,
}
(ROOT/'provenance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['queries','requests']},ensure_ascii=False),flush=True)
