import importlib.util, json, re, tempfile, unittest, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('importer', ROOT/'scripts/import_course.py');imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)

class ImportSecurity(unittest.TestCase):
    def test_zip_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'malicious.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../outside.txt','bad')
            with self.assertRaises(ValueError):imp.safe_extract(p,Path(tmp)/'target')
    def test_html_active_content(self):
        result=imp.MarkdownHTML().markdown('<p>Текст</p><script>secret()</script><iframe>closed</iframe><pre><code>if x:\n    print(x)</code></pre>')
        self.assertNotIn('secret',result);self.assertNotIn('closed',result);self.assertIn('    print(x)',result)
    def test_student_link_candidates(self):
        self.assertIsNone(imp.student_url('https://edu.future.ismart.org/teacher/dashboard/courses'))
        candidate=imp.student_url('https://edu.future.ismart.org/course/practice/0/unit/abc/element/def?back=%2Fteacher%2Fdashboard&token=hidden')
        self.assertEqual(candidate,'https://edu.future.ismart.org/course/practice/0/unit/abc/element/def')
    def test_content_integrity_and_teacher_exclusion(self):
        content=ROOT/'public/content';index=imp.load(content/'index.json')
        self.assertEqual(index['counts']['sections'],82);self.assertEqual(index['counts']['slides'],1239)
        ids=set();all_tasks=set();slides=0;presentations=0
        for r in index['lessons']:
            self.assertNotIn(r['id'],ids);ids.add(r['id']);l=imp.load(content/'lessons'/f"{r['id']}.json")
            for t in l['tasks']:
                self.assertNotIn(t['id'],all_tasks);all_tasks.add(t['id'])
                if t['type']=='assessment':self.assertIsNone(t['solution']);self.assertEqual(t['variants'],[])
                if t['ismartLink']:self.assertEqual(t['ismartLink']['status'],'unverified')
            for uri in l['slides']:
                self.assertTrue((ROOT/'public'/uri.lstrip('/')).is_file());slides+=1
            if l['deckDownload']:
                presentations+=1
                with zipfile.ZipFile(ROOT/'public'/l['deckDownload'].lstrip('/')) as z:
                    self.assertFalse(any(n.startswith(('ppt/notes','ppt/comments','docProps/')) for n in z.namelist()))
                    self.assertFalse(any(b'/teacher/' in z.read(n) for n in z.namelist() if n.endswith('.rels')))
            for f in l['files']:
                p=ROOT/'public'/f['url'].lstrip('/');self.assertTrue(p.is_file());self.assertEqual(imp.sha(p.read_bytes()),f['sha256'])
        self.assertEqual(len(ids),82);self.assertEqual(slides,1239);self.assertEqual(presentations,74)
        self.assertEqual(len(all_tasks),index['counts']['tasks']);self.assertIn('M03-L16',ids);self.assertIn('M03-L17',ids)
        for p in content.rglob('*'):
            if p.suffix in ('.json','.svg'):
                s=p.read_text(encoding='utf-8');self.assertNotIn('/teacher/',s,str(p));self.assertNotIn('OneDrive',s,str(p));self.assertNotRegex(s,r'(?i)(?:access_token|bearer [a-z0-9_-]{20})')
        self.assertFalse(any(p.suffix=='.docx' for p in content.rglob('*')))

if __name__=='__main__':unittest.main()
