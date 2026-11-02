"""Execute authored textbook examples independently; record their exact fixture hashes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from importlib.metadata import version
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]

def fixture_hash(example):
    return hashlib.sha256(json.dumps({key:example.get(key,'') for key in ['code','input','expected']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def run(case):
    topic,index,example=case
    with tempfile.TemporaryDirectory(prefix='cfa-knowledge-') as folder:
        path=Path(folder)/'example.py'
        path.write_text(example['code'],encoding='utf8')
        env={**os.environ,'PYTHONIOENCODING':'utf-8','MPLBACKEND':'Agg','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0'}
        try:
            result=subprocess.run([sys.executable,'-X','utf8',str(path)],cwd=folder,input=example.get('input',''),capture_output=True,text=True,encoding='utf8',timeout=40,env=env)
            actual=result.stdout.replace('\r\n','\n').rstrip('\n')
            expected=example['expected'].replace('\r\n','\n').rstrip('\n')
            failure=None if result.returncode==0 and actual==expected else {'topic':topic,'example':index,'exitCode':result.returncode,'expected':expected,'actual':actual,'stderr':result.stderr[-3000:]}
        except subprocess.TimeoutExpired:
            failure={'topic':topic,'example':index,'error':'Timed out after 40 seconds'}
    return {'topic':topic,'example':index,'fixtureSha256':fixture_hash(example)},failure

def verify():
    started=time.time();cases=[]
    for path in sorted((ROOT/'content/knowledge/chapters').glob('*.json')):
        chapter=json.loads(path.read_text(encoding='utf8'))
        for index,example in enumerate(chapter['examples'],1):cases.append((chapter['id'],index,example))
    fixtures=[];failures=[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        for result,failure in executor.map(run,cases):
            fixtures.append(result)
            if failure:failures.append(failure);print(json.dumps(failure,ensure_ascii=False),flush=True)
    report={'reviewedAt':date.today().isoformat(),'python':sys.version.split()[0],'libraries':{name:version(name) for name in ['numpy','pandas','scikit-learn','matplotlib']},'chapters':len({case[0] for case in cases}),'examples':len(cases),'passed':len(cases)-len(failures),'failures':failures,'fixtures':fixtures}
    target=ROOT/'content/knowledge/verification.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f"Knowledge examples: {report['passed']}/{len(cases)} passed in {time.time()-started:.1f}s",flush=True)
    return not failures
if __name__=='__main__':sys.exit(0 if verify() else 1)
