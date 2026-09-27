"""Build the RMV corpus from saved Crossref, PubMed and Europe PMC responses.

Python 3.10+, standard library only. See source-manifest.json for queries.
Usage: python scripts/build_dataset.py --source-root ../../work --cutoff 2026-09-27
"""
import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default

def clean(value):
    value = re.sub(r'<(?:\w+:)?title[^>]*>\s*abstract\s*</(?:\w+:)?title>', '', value or '', flags=re.I)
    value = re.sub(r'</(?:\w+:)?(?:p|sec)>', '\n\n', value, flags=re.I)
    value = html.unescape(re.sub(r'</?[A-Za-z][A-Za-z0-9:_-]*(?:\s[^<>]*?)?\s*/?>', '', value))
    return re.sub(r'[ \t\r\f\v]+', ' ', value).strip()

def normalized(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', clean(value)).lower())

def date_parts(record, field):
    parts = record.get(field, {}).get('date-parts', [[]])[0]
    return '-'.join(str(v) if i == 0 else f'{v:02}' for i, v in enumerate(parts)) or None

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--cutoff', default='2026-09-27')
    args = parser.parse_args()
    src, cutoff = args.source_root, args.cutoff
    cr_issue = read(src/'source_audit/crossref_issue_year.json')['message']['items']
    cr_online = read(src/'source_audit/crossref.json')['message']['items']
    epmc_response = read(src/'pubmed/epmc_complete.json') or read(src/'source_audit/epmc_issue_year.json')
    epmc = epmc_response['resultList']['result']
    pubmed = read(src/'pubmed/records.json')
    supplements = read(src/'source_audit/supplements.json', {})
    keyword_supplements = read(src/'pubmed/keyword_supplements.json', {})
    title_supplements = read(src/'pubmed/title_supplements.json', {})
    # Supplements are keyed by canonical DOI; values must have a source URL.
    epmc_doi = {r['doi'].lower():r for r in epmc if r.get('doi') and r.get('source') == 'MED'}
    epmc_title = {normalized(r['title']):r for r in epmc if r.get('source') == 'MED'}
    pm_title = {normalized(r['title']):r for r in pubmed.values()}
    cr = {r['DOI'].lower():r for r in [*cr_online,*cr_issue]}
    articles, excluded, corrections, date_conflicts = [], [], [], []
    for doi, r in cr.items():
        title = clean(' '.join(r.get('title', [])))
        reason = 'journal_issue_record' if r['type'] == 'journal-issue' else ('front_matter' if title.lower() in ('issue information','cover image') else None)
        if reason:
            excluded.append({'doi':doi,'title':title or None,'reason':reason,'crossref_type':r['type']})
            continue
        online, print_date = date_parts(r,'published-online'), date_parts(r,'published-print')
        year = int(print_date[:4]) if print_date else int(online[:4]) if online else None
        if year not in (2024,2025,2026):
            continue
        if online and online > cutoff:
            excluded.append({'doi':doi,'title':title,'reason':'online_date_after_cutoff'})
            continue
        p = pubmed.get(doi) or pm_title.get(normalized(title)) or {}
        e = epmc_doi.get(doi) or epmc_title.get(normalized(title)) or {}
        s = supplements.get(doi,{}) if isinstance(supplements,dict) else {}
        k = keyword_supplements.get(doi,{}) if isinstance(keyword_supplements,dict) else {}
        t = title_supplements.get(doi,{})
        if p.get('doi') and p['doi'] != doi:
            corrections.append({'canonical_doi':doi,'source_doi':p['doi'],'reason':'exact_normalized_title_match_to_publisher_Crossref_record','pmid':p['pmid']})
        if e.get('pubYear') and int(e['pubYear']) != year:
            date_conflicts.append({'doi':doi,'crossref_issue_year':year,'epmc_pub_year':e['pubYear']})
        abstract = clean(p.get('abstract') or r.get('abstract') or e.get('abstractText') or s.get('abstract') or '') or None
        abstract_source = 'PubMed' if p.get('abstract') else 'Crossref' if r.get('abstract') else 'Europe PMC' if e.get('abstractText') else 'Wiley' if s.get('abstract') else None
        keywords = p.get('author_keywords') or k.get('keywords') or k.get('author_keywords') or s.get('keywords') or []
        keyword_source = 'PubMed KeywordList' if p.get('author_keywords') else k.get('source_url') if keywords and k else s.get('source_url') if keywords and s else None
        # EPMC may normalize keyword casing; use it only when no original list exists.
        if not keywords and e.get('keywordList',{}).get('keyword'):
            keywords=e['keywordList']['keyword']; keyword_source='Europe PMC keywordList (source-normalized casing)'
        pmid=p.get('pmid') or e.get('pmid') or s.get('pmid')
        urls={'publisher':'https://onlinelibrary.wiley.com/doi/'+doi,'crossref':'https://api.crossref.org/works/'+doi}
        if pmid:
            urls.update(pubmed=f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',europe_pmc=f'https://europepmc.org/article/MED/{pmid}')
        if k.get('source_url'): urls['keyword_supplement']=k['source_url']
        if s.get('source_url'): urls['publisher_supplement']=s['source_url']
        if t.get('source_url'): urls['title_supplement']=t['source_url']
        articles.append({
            'doi':doi,'title':t.get('title') or title,'crossref_title':title,'abstract':abstract,'keywords':list(dict.fromkeys(keywords)),
            'year':year,'year_basis':'Crossref published-print' if print_date else 'Crossref published-online (not yet assigned to issue)',
            'journal':'Reviews in Medical Virology','journal_short':'RMV','issn':['1099-1654','1052-9276'],
            'volume':r.get('volume'),'issue':r.get('issue'),'published_online':online,'published_print':print_date,
            'online_year':int(online[:4]) if online else None,'pmid':pmid,'pmcid':e.get('pmcid'),
            'authors':[{'given':a.get('given',''),'family':a.get('family',''),'orcid':a.get('ORCID')} for a in r.get('author',[])],
            'publication_types':p.get('publication_types') or e.get('pubTypeList',{}).get('pubType') or ([s['publication_type']] if s.get('publication_type') else ['Journal Article (Crossref; subtype unavailable)']),
            'mesh_terms':[m['descriptorName'] for m in e.get('meshHeadingList',{}).get('meshHeading',[]) if m.get('descriptorName')],
            'field_sources':{'title':'Wiley article page (title and subtitle)' if t else 'Crossref (publisher-deposited)','abstract':abstract_source,'keywords':keyword_source,'dates':'Crossref (publisher-deposited)','publication_types':'PubMed' if p.get('publication_types') else 'Europe PMC' if e.get('pubTypeList') else s.get('publication_type_source','Crossref')},
            'field_status':{'abstract':'available' if abstract else 'not_in_retrieved_sources','keywords':'available' if keywords else 'not_in_retrieved_sources'},
            'source_urls':urls,'copyright_statement':p.get('copyright_statement') or None,
            'license_urls':sorted({x['URL'] for x in r.get('license',[]) if x.get('URL')}),
            'retrieved_on':cutoff,'notes':(['PubMed DOI differs; canonical publisher DOI used; title matched.'] if p.get('doi') and p['doi']!=doi else [])+([t.get('note','Publisher title supplement verified.')] if t else [])
        })
    articles.sort(key=lambda a:(a['year'],a['published_online'] or '',a['doi']),reverse=True)
    data=ROOT/'data'
    write_json(data/'articles.json',articles)
    (data/'articles.jsonl').write_text(''.join(json.dumps(a,ensure_ascii=False)+'\n' for a in articles),encoding='utf-8')
    fields=['doi','year','online_year','published_online','published_print','volume','issue','title','abstract','keywords','pmid','publication_types','abstract_source','keywords_source','publisher_url']
    with (data/'articles.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for a in articles:
            row={key:a.get(key) for key in fields};row.update(keywords='; '.join(a['keywords']),publication_types='; '.join(a['publication_types']),abstract_source=a['field_sources']['abstract'],keywords_source=a['field_sources']['keywords'],publisher_url=a['source_urls']['publisher']);writer.writerow(row)
    for a in articles: write_json(data/'articles'/f"{a['doi'].split('/')[1]}.json",a)
    counts={str(y):{'records':sum(a['year']==y for a in articles),'with_abstract':sum(a['year']==y and bool(a['abstract']) for a in articles),'with_keywords':sum(a['year']==y and bool(a['keywords']) for a in articles)} for y in (2024,2025,2026)}
    report={'cutoff_date':cutoff,'coverage':'2024 and 2025 issue-year records; 2026 year-to-date. Completeness is relative to the retrieved Crossref and PubMed/Europe PMC indexes, not certified publisher archival completeness.',
            'total_records':len(articles),'by_issue_year':counts,'by_online_year':dict(Counter(str(a['online_year']) for a in articles)),
            'crossref_issue_query_records':len(cr_issue),'crossref_publication_date_query_records':len(cr_online),'epmc_query_records':len(epmc),
            'excluded_records':excluded,'identifier_corrections':corrections,'year_disagreements':date_conflicts,
            'missing_abstract_dois':[a['doi'] for a in articles if not a['abstract']],
            'missing_keywords_dois':[a['doi'] for a in articles if not a['keywords']],
            'duplicate_dois':len(articles)-len({a['doi'] for a in articles}),
            'notes':['No AI-generated abstracts or keywords.','MeSH is stored separately and never substituted for author keywords.','Cross-year online and issue dates are retained independently.','2026 is not a completed full-year dataset.','Keywords absent from retrieved sources may exist elsewhere; absence is not proof that authors supplied none.']}
    coverage_paths=[src/'source_audit/wiley_2024_coverage.json',src/'wiley_2025_coverage.json',src/'pubmed/wiley_2026_coverage.json']
    report['publisher_toc_audit_files']=[]
    for path in coverage_paths:
        if path.exists():
            write_json(data/'coverage'/path.name,read(path))
            report['publisher_toc_audit_files'].append('coverage/'+path.name)
    report['publisher_toc_audit_summary']=('2024: all 106 content DOI links in six issues matched. 2025: issues 2-6 (65 records) matched by title/issue, 35 links also resolved to DOI; issue 1 (7 records) not independently verified against unavailable Wiley TOC. 2026: five published issues, 116 titles matched; 91 DOI links resolved, 25 article-link fetches unavailable. Detailed evidence and limitations are in coverage files.' if cutoff=='2026-09-27' and len(report['publisher_toc_audit_files'])==3 else 'No fresh publisher TOC verification is performed by the refresh script. Any retained coverage files are historical; check their individual audit dates before relying on them.')
    write_json(data/'quality-report.json',report)
    write_json(data/'missing-fields.json',[{'doi':a['doi'],'year':a['year'],'title':a['title'],'field_status':a['field_status'],'source_urls':a['source_urls']} for a in articles if not a['abstract'] or not a['keywords']])
    for year in (2024,2025,2026):
        yearly=[a for a in articles if a['year']==year]
        write_json(data/f'{year}.json',yearly)
        md=[f'# RMV {year} 年文献',f'采集截止：{cutoff}。按期刊卷期年归档。共 {len(yearly)} 条。'+('2026 年尚未结束。' if year==2026 else ''),'']
        for a in yearly:
            md += [f"## {a['title']}",f"DOI: [{a['doi']}]({a['source_urls']['publisher']}) | 在线日期: {a['published_online']} | 卷期: {a['volume']}({a['issue']})",'',f"关键词：{'；'.join(a['keywords']) or '来源未获取'}",'',a['abstract'] or '摘要：来源未提供。','']
        (data/f'{year}.md').write_text('\n'.join(md),encoding='utf-8')
    (data/'catalogue.md').write_text('# RMV 文献目录\n\n'+ '\n'.join(f"- [{a['year']}] [{a['title']}]({a['source_urls']['publisher']}) · `{a['doi']}`" for a in articles)+'\n',encoding='utf-8')
    manifest={'retrieved_on':cutoff,'journal_url':'https://onlinelibrary.wiley.com/journal/10991654','cutoff_policy':'Exclude items whose known online publication date is after cutoff. Preserve earlier-online papers assigned to requested issue years.',
        'queries':[
            {'source':'Crossref issue dates','url':'https://api.crossref.org/journals/1099-1654/works?filter=from-print-pub-date:2024-01-01,until-print-pub-date:2026-12-31&rows=1000'},
            {'source':'Crossref publication dates','url':'https://api.crossref.org/journals/1099-1654/works?filter=from-pub-date:2024-01-01,until-pub-date:2026-12-31&rows=1000'},
            {'source':'Europe PMC','query':'(ISSN:1099-1654 OR ISSN:1052-9276) AND PUB_YEAR:[2024 TO 2026]','url':'https://www.ebi.ac.uk/europepmc/webservices/rest/search','resultType':'core'},
            {'source':'PubMed','url':'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi','db':'pubmed','retmode':'xml','method':'Batched PMID lists from journal query'}],
        'raw_input_sha256':{str(path.relative_to(src)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [src/'source_audit/crossref_issue_year.json',src/'source_audit/crossref.json',src/'pubmed/records.json',src/'pubmed/epmc_complete.json'] if path.exists()},
        'dataset_sha256':hashlib.sha256((data/'articles.json').read_bytes()).hexdigest()}
    write_json(data/'source-manifest.json',manifest)
    print(json.dumps({'total':len(articles),'by_year':counts,'excluded':len(excluded),'missing_abstract':len(report['missing_abstract_dois']),'missing_keywords':len(report['missing_keywords_dois']),'corrections':corrections},ensure_ascii=False))

if __name__=='__main__': main()
