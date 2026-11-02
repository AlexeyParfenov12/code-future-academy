from pathlib import Path
import ast,csv,hashlib,json,subprocess,sys,tempfile,unittest,zipfile
ROOT=Path(__file__).resolve().parents[1]
read=lambda path:json.loads(path.read_text(encoding='utf8'))
class AssessmentSolutions(unittest.TestCase):
    def test_every_available_condition_has_review_and_matching_source(self):
        report=read(ROOT/'public/content/assessment-coverage.json')
        self.assertEqual((report['tasks'],report['conditions'],report['publishedConditions']),(268,346,344))
        self.assertEqual(len(report['missingConditions']),2)
        self.assertEqual({m['assessmentId'] for m in report['missingConditions']},{'M02-L18'})
        seen=set()
        for path in (ROOT/'content/assessments').glob('*.json'):
            work=read(path)
            public=read(ROOT/'public/content/assessments'/path.name)
            self.assertEqual(len(work['tasks']),len(public['tasks']))
            for task in work['tasks']:
                for variant in task['variants']:
                    self.assertNotIn(variant['id'],seen);seen.add(variant['id'])
                    self.assertNotIn('Верный ответ:',variant['statement'])
                    self.assertNotIn('Материалы для учителя',variant['statement'])
                    self.assertEqual(hashlib.sha256(variant['statement'].encode()).hexdigest(),variant['source']['conditionSha256'])
                    review=variant['solution']
                    if review['status']=='unavailable':
                        self.assertIn('нет',review['reason'].lower());continue
                    self.assertTrue(review['authorization']);self.assertTrue(review['explanation'])
                    self.assertEqual(hashlib.sha256((review['code'] or review['answer']).encode()).hexdigest(),review['sha256'])
                    for option in review.get('selectedOptions',[]):self.assertIn(option,variant['statement'])
    def test_all_reviewed_program_fixtures_execute(self):
        count=0
        for path in (ROOT/'content/assessments').glob('*.json'):
            for task in read(path)['tasks']:
                for variant in task['variants']:
                    solution=variant['solution']
                    if not solution.get('code'):continue
                    tree=ast.parse(solution['code'])
                    for node in ast.walk(tree):
                        if isinstance(node,ast.Import):names=[n.name.split('.')[0] for n in node.names]
                        elif isinstance(node,ast.ImportFrom):names=[node.module.split('.')[0]]
                        else:names=[]
                        self.assertTrue(set(names)<={'argparse','json','math','re','collections','statistics'})
                    for case in solution['tests']:
                        with tempfile.TemporaryDirectory() as tmp:
                            file=Path(tmp)/'solution.py';file.write_text(solution['code'],encoding='utf8')
                            result=subprocess.run([sys.executable,'-X','utf8',str(file)],cwd=tmp,input=case['input'],capture_output=True,text=True,timeout=15)
                            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),case['expected'].strip())
                        count+=1
        self.assertEqual(count,11)
    def test_final_project_archive_and_real_metrics(self):
        with zipfile.ZipFile(ROOT/'public/content/examples/final-message-risk.zip') as archive:
            manifest=json.loads(archive.read('manifest.json'))
            for name,sha in manifest['files'].items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),sha)
            result=json.loads(archive.read('results.json'))
            self.assertEqual((result['trainRows'],result['testRows']),(40,10))
            self.assertEqual((result['tp'],result['fp'],result['fn'],result['tn']),(5,0,0,5))
            self.assertEqual(result['baselineAccuracy'],.5)
            with tempfile.TemporaryDirectory() as tmp:
                archive.extractall(tmp)
                run=subprocess.run([sys.executable,'-X','utf8','main.py'],cwd=tmp,capture_output=True,text=True,timeout=10)
                self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout),result)
                with (Path(tmp)/'train.csv').open(encoding='utf8') as stream:train=list(csv.DictReader(stream))
                with (Path(tmp)/'test.csv').open(encoding='utf8') as stream:test=list(csv.DictReader(stream))
                self.assertEqual((len(train),len(test)),(40,10))
                self.assertFalse({r['text'] for r in train}&{r['text'] for r in test})
if __name__=='__main__':unittest.main()
