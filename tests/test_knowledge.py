import hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text(encoding='utf8'))

class KnowledgeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapters={p.stem:load(p) for p in (ROOT/'content/knowledge/chapters').glob('*.json')}
        cls.index=load(ROOT/'public/content/knowledge/index.json')
        cls.proof=load(ROOT/'content/knowledge/verification.json')

    def test_expansion_preserves_old_routes_and_covers_both_tracks(self):
        old='variables types output input conversion arithmetic strings conditions logic loops lists dictionaries functions csv tables cleaning statistics charts features target split classification regression clustering metrics overfitting problem dataset prototype testing documentation defense'.split()
        self.assertTrue(set(old)<=self.chapters.keys())
        self.assertEqual(sum(c['track']=='python' for c in self.chapters.values()),72)
        self.assertEqual(sum(c['track']=='ai' for c in self.chapters.values()),73)
        self.assertEqual(len({c['order'] for c in self.chapters.values()}),145)
        lesson_ids={l['id'] for l in load(ROOT/'public/content/index.json')['lessons']}
        for c in self.chapters.values():
            self.assertTrue(set(c['prerequisites']+c['related'])<=self.chapters.keys())
            self.assertTrue(c['lessons'] and set(c['lessons'])<=lesson_ids,c['id'])

    def test_published_code_and_outputs_match_executed_fixtures(self):
        self.assertEqual(self.proof['failures'],[])
        self.assertEqual(self.proof['passed'],156)
        proof={(p['topic'],p['example']):p['fixtureSha256'] for p in self.proof['fixtures']}
        fence=chr(96)*3
        for c in self.chapters.values():
            public=load(ROOT/'public/content/knowledge/topics'/f"{c['id']}.json")
            self.assertEqual(public['content'],c['content'])
            self.assertTrue(public['examplesVerified'])
            blocks=re.findall(fence+r'python\n(.*?)\n'+fence,c['content'],re.S)
            self.assertEqual(blocks,[e['code'] for e in c['examples']],c['id'])
            for i,e in enumerate(c['examples'],1):
                digest=hashlib.sha256(json.dumps({k:e.get(k,'') for k in ['code','input','expected']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                self.assertEqual(digest,proof[(c['id'],i)])
                self.assertIn(fence+'text\n'+e['expected'].rstrip('\n')+'\n'+fence,c['content'])

    def test_resources_have_concrete_start_limits_and_valid_topic_links(self):
        resources=self.index['resources']
        self.assertEqual(len(resources),94)
        self.assertEqual(len({r['url'] for r in resources}),94)
        for r in resources:
            self.assertTrue(r['url'].startswith('https://'))
            self.assertTrue(r['start'] and r['limits'] and r['verifiedAt'])
            self.assertEqual(r['verification']['status'],200)
            self.assertTrue(r['verification']['title'].strip())
            self.assertTrue(set(r['topics'])<=self.chapters.keys(),r['id'])
        source_ids={r['id'] for r in resources}
        for t in self.index['topics']:
            self.assertNotIn('content',t)
            self.assertTrue(set(t['sourceIds'])<=source_ids)

    def test_new_chapters_are_in_full_text_search_without_duplicate_records(self):
        search=load(ROOT/'public/content/search-index.json')
        self.assertEqual(len(search),len({s['id'] for s in search}))
        records={r['id']:r for r in search}
        for ident,c in self.chapters.items():
            record=records['topic-'+ident]
            self.assertEqual(record['url'],'/textbook/'+ident)
            self.assertEqual(record['body'],c['content'])
        self.assertEqual(sum(r['id'].startswith('knowledge-resource-') for r in search),94)
if __name__=='__main__':unittest.main()
