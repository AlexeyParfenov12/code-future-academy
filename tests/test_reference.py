import ast,hashlib,importlib.util,json,sys,unittest,zipfile,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import reference_content as ref
load=lambda path:json.loads(path.read_text(encoding='utf8'))

class ReferenceContract(unittest.TestCase):
    def test_condition_keeps_siblings_and_does_not_import_key(self):
        capture={'html':'<div data-legacy-markup-content><p>Условие</p><p>Вторая часть</p><pre>if x:\n    print("a\\nb")</pre></div>','text':'А) Первый\nВерный ответ:\nБ) Секрет'}
        value=ref.capture_markdown(capture)
        self.assertIn('Вторая часть',value);self.assertIn('    print("a\\nb")',value)
        self.assertIn('А) Первый',value);self.assertNotIn('Секрет',value)
    def test_assessment_navigation_contains_outline_only(self):
        data=load(ROOT/'public/content/assessments.json')
        self.assertEqual(data['counts'],{'control':8,'assessment':4,'final':1})
        self.assertEqual(len(data['entries']),13)
        allowed={'id','moduleId','order','number','title','kind','candidateUrl','linkStatus','documentUrl','url','taskCount','solutionCount'}
        for entry in data['entries']:
            self.assertTrue(set(entry)<=allowed)
            if entry['kind']=='control':
                self.assertEqual(entry['linkStatus'],'unverified')
                self.assertIn('https://edu.future.ismart.org/course/practice/',entry['candidateUrl'])
                self.assertNotIn('?',entry['candidateUrl'])
            else:self.assertTrue((ROOT/'public/content/lessons'/f"{entry['id']}.json").is_file())
    def test_native_question_excludes_teacher_answer(self):
        value=ref.capture_markdown({'text':'Задание:\nСопоставьте А и Б\nВерный ответ:\nА=42','html':''})
        self.assertIn('Сопоставьте',value);self.assertNotIn('А=42',value)
    def test_indent_requires_exact_trusted_source(self):
        good='if x:\n    print("a\\nb")'
        value=ref.format_lecture('Пример на слайде:\nif x:\nprint("a\\nb")',[good])
        self.assertIn('    print("a\\nb")',value)
        changed=ref.format_lecture('Пример на слайде:\nif x:\nprint("другое")',[good])
        self.assertNotIn('    print(',changed)
        spaces=ref.format_lecture('Пример на слайде:\nif x:\nprint("a b")',['if x:\n    print("ab")'])
        self.assertIn('"a b"',spaces);self.assertNotIn('"ab"',spaces)
    def test_every_solution_has_evidence_and_unique_official_target(self):
        index=load(ROOT/'public/content/index.json')
        official={t['id']:l['id'] for l in index['lessons'] for t in l['tasks']}
        seen=set();count=0
        for path in (ROOT/'content/solutions').glob('*.json'):
            for s in load(path)['solutions']:
                self.assertNotIn(s['taskId'],seen);seen.add(s['taskId'])
                self.assertEqual(official[s['taskId']],s['lessonId'])
                self.assertTrue(s['rightsConfirmed']);self.assertEqual(s['status'],'published')
                self.assertEqual(s['sha256'],hashlib.sha256((s['code'] or s['answer']).encode()).hexdigest())
                self.assertEqual(s['sha256'],s['verificationEvidence']['codeSha256'])
                self.assertEqual(s['testCount'],len(s['tests']));self.assertEqual(s['testCount'],s['verificationEvidence']['passed'])
                if s['code']:
                    ast.parse(s['code']);self.assertGreater(s['testCount'],0)
                    for line in s['lineExplanations']:self.assertLessEqual(line['line'],len(s['code'].splitlines()))
                count+=s['testCount']
        self.assertEqual(set(official),seen);self.assertGreater(count,200)
    def test_document_hashes_and_unmodified_original_pdfs(self):
        report=load(ROOT/'public/content/document-report.json')
        self.assertEqual((report['lecturePdfs'],report['originalPdfs'],report['presentationPdfs']),(74,13,36))
        self.assertEqual(report['htmlConversions'],61)
        self.assertEqual(len(report['missingOriginalPresentations']),38)
        self.assertEqual(len(report['documents']),110)
        for doc in report['documents']:
            data=(ROOT/'public/content/documents'/doc['file']).read_bytes()
            self.assertTrue(data.startswith(b'%PDF-'));self.assertEqual(hashlib.sha256(data).hexdigest(),doc['sha256'])
            if not doc['derived']:self.assertEqual(doc['sha256'],doc['sourceSha256'])
    def test_separate_316_317_and_canonical_counts(self):
        a=load(ROOT/'public/content/lessons/M03-L16.json');b=load(ROOT/'public/content/lessons/M03-L17.json')
        self.assertNotEqual({t['id'] for t in a['tasks']},{t['id'] for t in b['tasks']})
        self.assertIn('iris',str(a).lower());self.assertNotIn('iris_dirty',str(b).lower())
        coverage=load(ROOT/'public/content/solution-coverage.json')
        self.assertEqual([m['officialTasks'] for m in coverage['modules']],[112,130,62,77,0])
        self.assertEqual(coverage['published'],381)
        self.assertEqual(sum(m['verifiedIsmartLinks'] for m in coverage['modules']),0)
    def test_downloadable_example_runs_and_matches_manifest(self):
        with zipfile.ZipFile(ROOT/'public/content/examples/campus-support-4-13.zip') as archive:
            manifest=json.loads(archive.read('manifest.json'))
            for name,sha in manifest['files'].items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),sha)
            self.assertEqual(json.loads(archive.read('docs/data-passport.json'))['rows'],64)
            with tempfile.TemporaryDirectory() as tmp:
                archive.extractall(tmp)
                run=subprocess.run([sys.executable,'-X','utf8','src/main_v2_0.py'],cwd=tmp,capture_output=True,text=True,timeout=10)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertEqual(run.stdout.strip(),archive.read('reports/expected-results.txt').decode().strip())
if __name__=='__main__':unittest.main()
