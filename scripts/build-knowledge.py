"""Build lazy chapter documents, compact navigation and full-text search."""
from pathlib import Path
import ast,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf8'))
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
def build(draft=False):
 source=ROOT/'content/knowledge';chapters=[read(p) for p in sorted((source/'chapters').glob('*.json'))]
 chapters.sort(key=lambda c:c.get('order',999))
 ids={c['id'] for c in chapters};resources=read(source/'resources.json')
 verification=read(source/'verification.json') if (source/'verification.json').exists() else {}
 verified={(v['topic'],v['example']):v['fixtureSha256'] for v in verification.get('fixtures',[])} if not verification.get('failures',True) else {}
 if not draft:
  assert len(chapters)>=140,'Knowledge expansion is incomplete'
  assert len(resources)>=90
  assert all(r['verifiedAt'] for r in resources),'Unverified resource address'
 metadata=[];fixtures=0;words=0
 for chapter in chapters:
  assert re.fullmatch('[a-z0-9-]+',chapter['id'])
  assert chapter['track'] in ['python','ai'] and chapter['level'] in ['beginner','intermediate','advanced']
  assert len(chapter['content'])>900 and chapter['summary']
  if not draft:
   for reference in chapter['prerequisites']+chapter['related']:assert reference in ids,reference
  chapter_verified=True
  for index,example in enumerate(chapter['examples'],1):
   ast.parse(example['code']);assert hashlib.sha256(example['code'].encode()).hexdigest()==example['sha256']
   digest=hashlib.sha256(json.dumps({key:example.get(key,'') for key in ['code','input','expected']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
   chapter_verified=chapter_verified and verified.get((chapter['id'],index))==digest
   if not draft:assert chapter_verified,('Example requires replay',chapter['id'],index)
  sources=[r['id'] for r in resources if chapter['id'] in r['topics']]
  count=len(re.findall(r'\S+',chapter['content']));words+=count;fixtures+=len(chapter['examples'])
  meta={k:v for k,v in chapter.items() if k not in ['content','examples']}
  meta.update(contentUrl='/content/knowledge/topics/'+chapter['id']+'.json',readingMinutes=max(2,round(count/160)),exampleCount=len(chapter['examples']),sourceIds=sources,keywords=' '.join(sorted(set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_.]{2,50}\b',chapter['content'])))))
  metadata.append(meta)
  write(ROOT/'public/content/knowledge/topics'/f"{chapter['id']}.json",{'id':chapter['id'],'content':chapter['content'],'examplesVerified':chapter_verified,'reviewedAt':verification.get('reviewedAt') if chapter_verified else None})
 if not draft:
  for resource in resources:
   for topic in resource['topics']:assert topic in ids,(resource['id'],topic)
 report={'topics':len(chapters),'pythonTopics':sum(c['track']=='python' for c in chapters),'aiTopics':sum(c['track']=='ai' for c in chapters),'resources':len(resources),'verifiedResources':sum(bool(r['verifiedAt']) for r in resources),'examples':fixtures,'verifiedExamples':len(verified),'wordsIncludingCode':words,'lazyLoading':True,'reviewedAt':verification.get('reviewedAt')}
 write(ROOT/'src/generated/knowledge-index.json',{'topics':metadata,'resources':[{k:v for k,v in resource.items() if k!='verification'} for resource in resources],'report':report})
 write(ROOT/'public/content/knowledge/index.json',{'topics':metadata,'resources':resources,'report':report})
 write(ROOT/'public/content/knowledge/report.json',report)
 search_path=ROOT/'public/content/search-index.json'
 search=[r for r in read(search_path) if not r['id'].startswith(('topic-','knowledge-resource-'))]
 for chapter in chapters:search.append({'id':'topic-'+chapter['id'],'title':chapter['title'],'context':('Учебник Python' if chapter['track']=='python' else 'Искусственный интеллект')+' / '+chapter['group'],'url':'/textbook/'+chapter['id'],'body':chapter['content']})
 for resource in resources:search.append({'id':'knowledge-resource-'+resource['id'],'title':resource['title'],'context':'Источники и инструменты / '+resource['category'],'url':'/resources?q='+resource['title'],'body':resource['description']+' '+resource['start']})
 write(search_path,search);print(json.dumps(report))
if __name__=='__main__':build('--draft' in sys.argv)
