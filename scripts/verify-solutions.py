"""Replay reviewed ordinary-practice fixtures in isolated temporary directories."""
from pathlib import Path
import argparse,ast,hashlib,json,os,shutil,subprocess,sys,tempfile,time

ROOT=Path(__file__).resolve().parents[1]
def verify(lesson=None):
    started=time.time();passed=0;solutions=0;failures=[]
    for path in sorted((ROOT/'content/solutions').glob('*.json')):
        for item in json.loads(path.read_text(encoding='utf8'))['solutions']:
            if lesson and item['lessonId']!=lesson:continue
            solutions+=1
            value=item.get('code') or item['answer']
            if hashlib.sha256(value.encode()).hexdigest()!=item['sha256']:raise ValueError('Checksum: '+item['taskId'])
            if not item.get('code'):continue
            tree=ast.parse(item['code'])
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):names=[n.name.split('.')[0] for n in node.names]
                elif isinstance(node,ast.ImportFrom):names=[(node.module or '').split('.')[0]]
                else:names=[]
                if set(names)&{'os','subprocess','socket','requests','urllib','http','shutil','ctypes','winreg'}:raise ValueError('Unapproved import')
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'eval','exec','compile','__import__'}:raise ValueError('Unapproved execution')
            record=json.loads((ROOT/'public/content/lessons'/f"{item['lessonId']}.json").read_text(encoding='utf8'))
            for case in item['tests']:
                with tempfile.TemporaryDirectory(prefix='cfa-reviewed-') as tmp:
                    folder=Path(tmp)
                    for file in record['files']:
                        if file['type'] in ['csv','json','ipynb']:shutil.copyfile(ROOT/'public'/file['url'].lstrip('/'),folder/Path(file['name']).name)
                    script=folder/'solution.py';script.write_text(item['code']+'\n'+case.get('harness',''),encoding='utf8')
                    env=os.environ.copy();env.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','MPLBACKEND':'Agg','PYTHONIOENCODING':'utf-8'})
                    try:
                        result=subprocess.run([sys.executable,'-X','utf8',str(script)],input=case['input'],text=True,capture_output=True,cwd=folder,env=env,timeout=30)
                        actual=result.stdout.replace('\r\n','\n').rstrip('\n')
                        if result.returncode or actual!=case['expected'].rstrip('\n'):
                            failures.append({'taskId':item['taskId'],'error':result.stderr[-1200:],'expected':case['expected'],'actual':actual})
                        else:passed+=1
                    except subprocess.TimeoutExpired:failures.append({'taskId':item['taskId'],'error':'timeout 30s'})
            print(f"{item['lessonId']} {item['taskId']}: {len(item['tests'])} fixtures",flush=True)
    return {'solutions':solutions,'passed':passed,'failed':len(failures),'failures':failures,'python':sys.version,'seconds':round(time.time()-started,1)}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lesson');parser.add_argument('--report',type=Path);args=parser.parse_args()
    report=verify(args.lesson)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='failures'},ensure_ascii=False))
    if report['failed']:
        print(json.dumps(report['failures'],ensure_ascii=False,indent=2));sys.exit(1)
