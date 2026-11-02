"""Publish individually reviewed assessment explanations; no raw teacher archive."""
from pathlib import Path
import ast,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf8'))
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def build():
 content=ROOT/'public/content';destination=content/'assessments';destination.mkdir(exist_ok=True)
 collections=[];missing=[];published=0;conditions=0;task_count=0;tests=0
 for path in sorted((ROOT/'content/assessments').glob('*.json')):
  work=read(path);task_count+=len(work['tasks'])
  for task in work['tasks']:
   for variant in task['variants']:
    conditions+=1;s=variant['solution']
    if s['status']=='unavailable':missing.append({'assessmentId':work['id'],'taskId':task['id'],'title':task['title'],'reason':s['reason']});continue
    assert s['status']=='published' and s['authorization'] and s['reviewedAt'] and len(s['explanation'])>35
    value=s.get('code') or s['answer']
    assert hashlib.sha256(value.encode()).hexdigest()==s['sha256']
    assert s['testCount']==len(s.get('tests',[]))
    if s.get('code'):ast.parse(s['code']);assert s['testCount']>0
    for option in s.get('selectedOptions',[]):assert option in variant['statement']
    published+=1;tests+=s['testCount']
    variant['solution']={k:v for k,v in s.items() if k not in ['tests','authorization','reviewedAt','sha256','selectedOptions']}
  write(destination/path.name,work);collections.append(work)
 index=read(content/'assessments.json')
 for entry in index['entries']:
  work=next(w for w in collections if w['id']==entry['id'])
  entry.update(url='/assessments/'+entry['id'],taskCount=len(work['tasks']),solutionCount=sum(v['solution']['status']=='published' for t in work['tasks'] for v in t['variants']))
 index['answerCoverage']={'conditions':conditions,'published':published,'missing':len(missing)}
 write(content/'assessments.json',index)
 search=read(content/'search-index.json');search=[r for r in search if not r['id'].startswith('assessment-answer-')]
 for work in collections:
  for task in work['tasks']:
   search.append({'id':'assessment-answer-'+task['id'],'title':task['title'],'context':work['title'],'aliases':work['number']+' '+task['title'],'url':'/assessments/'+work['id']+'/task/'+task['id'],'body':' '.join(v['statement']+' '+v['solution'].get('answer','') for v in task['variants'])})
 write(content/'search-index.json',search)
 report={'collections':len(collections),'tasks':task_count,'conditions':conditions,'publishedConditions':published,'missingConditions':missing,'runtimeFixtures':tests,'ismartVerification':'not_performed'}
 write(content/'assessment-coverage.json',report)
 imported=read(content/'import-report.json')
 imported['counts'].update(assessmentTasks=task_count,assessmentConditions=conditions,assessmentSolutions=published,assessmentMissingConditions=len(missing))
 imported['publication']['assessmentAnswers']='reviewed_explanations_published_on_explicit_owner_request'
 imported['projection']['assessmentKeys']='reviewed_answers_published; raw_teacher_archive_private'
 write(content/'import-report.json',imported)
 example=ROOT/'content/project-examples/message-risk'
 files={p.name:p.read_bytes() for p in example.iterdir() if p.is_file()}
 files['manifest.json']=json.dumps({'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}},indent=2).encode()
 archive=content/'examples/final-message-risk.zip';archive.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive,'w') as z:
  for name,data in sorted(files.items()):
   info=zipfile.ZipInfo(name,(2026,11,2,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
 print(json.dumps({k:v for k,v in report.items() if k!='missingConditions'}))
if __name__=='__main__':build()
