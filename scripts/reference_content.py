"""Student reference projection. Raw archive and full course registry stay private.

No program from an archive is executed here. Only reviewed solution manifests are
published. Document source manifests are written outside the distributable tree.
"""
from pathlib import Path
import ast,collections,hashlib,io,json,re,shutil,tokenize,token
from bs4 import BeautifulSoup,Tag,NavigableString

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def dump(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def digest(data):return hashlib.sha256(data).hexdigest()

def program_kind(code,context=''):
    if re.search(r'вывод|результат|входн|ввод|expected|output',context,re.I):return 'text'
    try:
        tree=ast.parse(code)
        meaningful=any(isinstance(n,(ast.Assign,ast.AugAssign,ast.FunctionDef,ast.For,ast.While,ast.If,ast.Import,ast.ImportFrom)) or isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) for n in tree.body)
        return 'python' if meaningful else 'text'
    except SyntaxError:
        return 'python' if re.search(r'^(?:\s*(?:for|while|if|elif|def|class|import|from)\b|\s*\w+\s*=)',code,re.M) else 'text'

def preceding_label(node):
    parent=node
    for _ in range(3):
        previous=parent.find_previous_sibling()
        if previous:
            text=previous.get_text(' ',strip=True)
            if text:return text[-180:]
        if not parent.parent:break
        parent=parent.parent
    return ''

def html_markdown(node):
    if isinstance(node,NavigableString):return str(node)
    if not isinstance(node,Tag):return ''
    tag=node.name
    if node.get('id','').startswith('placeholder'):return '___'
    if tag in ['script','style','svg','button','input','textarea','iframe','form','object','embed']:return ''
    if tag=='pre':
        code=node.get_text().replace('\r\n','\n').replace('\r','\n').rstrip('\n')
        part=node.find_parent(attrs={'data-cc-part':True})
        context=(part.get('data-cc-part','') if part else '')+' '+preceding_label(node)
        return '\n\n```'+program_kind(code,context)+'\n'+code+'\n```\n\n'
    if tag=='code' or 'cc-inline-code' in node.get('class',[]):return '`'+node.get_text()+'`'
    if tag=='br':return '\n'
    if tag=='table':
        rows=[[cell.get_text(' ',strip=True).replace('|','\\|') for cell in row.find_all(['td','th'],recursive=False)] for row in node.find_all('tr')]
        rows=[row for row in rows if row]
        if not rows:return ''
        n=max(map(len,rows));rows=[row+['']*(n-len(row)) for row in rows]
        return '\n\n'+'\n'.join('| '+' | '.join(row)+' |' for row in [rows[0],['---']*n,*rows[1:]])+'\n\n'
    text=''.join(html_markdown(child) for child in node.children)
    if re.fullmatch(r'h[1-6]',tag):
        label=text.strip()
        if label in ['Верный ответ:','Задание:']:return ''
        return '\n\n'+'#'*min(4,int(tag[1]))+' '+label+'\n\n'
    if tag in ['strong','b']:return '**'+text+'**'
    if tag in ['em','i']:return '*'+text+'*'
    if tag=='li':return '\n- '+text.strip()+'\n'
    if tag in ['div','p','section','article','ul','ol']:return '\n\n'+text.strip()+'\n\n'
    return text

def capture_markdown(capture):
    soup=BeautifulSoup(capture.get('html',''),'html.parser')
    main=soup.select_one('[data-legacy-markup-content]') or soup.select_one('.cc-task') or soup.select_one('.cc-lesson') or soup.select_one('.ql-editor') or soup.find('article')
    if main is None:
        targets=soup.select('.c001')
        if targets:
            main=targets[0]
            for ancestor in targets[0].parents:
                if all(ancestor is other or ancestor in other.parents for other in targets):main=ancestor;break
            if len(targets)==1 and main.parent and main.parent.name not in ['body','html']:main=main.parent
    if main is None:
        text=capture.get('text','')
        for marker in ['Скачать PDF\n','Консоль\n']:
            if marker in text:text=text.split(marker,1)[1];break
        for code in capture.get('codes',[]):
            if code and code in text:text=text.replace(code,'\n\n```'+program_kind(code)+'\n'+code+'\n```\n\n',1)
    else:text=html_markdown(main)
    # Native matching widgets store their choices outside the rich-text body.
    # Keep the question side only; never import the teacher's answer panel.
    widget=capture.get('text','')
    if 'Задание:\n' in widget and 'Верный ответ:\n' in widget:
        text=widget.split('Задание:\n',1)[1].split('Верный ответ:\n',1)[0].strip()
    for line in capture.get('text','').split('Верный ответ:',1)[0].splitlines():
        if re.match(r'^[АБВГДЕA-E][).]\s',line) and line.strip() not in text:text+='\n- '+line.strip()
    text=re.sub(r'<span\s+id="placeholder[^"]*"\s*></span>', '___',text)
    text=re.sub(r'^.*(?:Материалы для учителя|Общий объем до|Занято: \d).*$', '',text,flags=re.M)
    text=re.sub(r'https?://[^\s)<>]+',lambda m:m[0] if '/teacher/' not in m[0] and 'back=' not in m[0] else '[служебная ссылка исключена]',text)
    return re.sub(r'\n{3,}','\n\n',text).strip()

def literal_tokens(code):
    """Whitespace inside a string is data and must never be 'repaired'."""
    kinds={token.STRING}
    kinds.update(getattr(token,name,-1) for name in ['FSTRING_START','FSTRING_MIDDLE','FSTRING_END'])
    try:return tuple(t.string for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type in kinds)
    except (tokenize.TokenError,IndentationError):return None

def format_lecture(text,verified_blocks=()):
    """Format explicit source markers; recover indent only by an exact source match."""
    for block in sorted(set(verified_blocks),key=len,reverse=True):
        block=block.strip('\n')
        if len(block)<20 or program_kind(block)!='python':continue
        try:ast.parse(block)
        except SyntaxError:continue
        # Repair a fragmented source span only if all non-whitespace characters
        # match a trusted complete block, including strings and punctuation.
        pattern=re.compile(r'\s*'.join(re.escape(c) for c in re.sub(r'\s+','',block)))
        for match in list(pattern.finditer(text))[::-1]:
            if literal_tokens(match[0])!=literal_tokens(block):continue
            if text[:match.start()].count('```')%2:continue
            prefix=text[:match.start()];suffix=text[match.end():]
            if prefix.rsplit('\n',1)[-1].strip() and not re.search(r'Пример на слайде:\s*$',prefix):continue
            if suffix.split('\n',1)[0].strip():continue
            prefix=re.sub(r'Пример на слайде:\s*$','',prefix)
            text=prefix+'\n\n```python\n'+block+'\n```\n\n'+suffix
    known={(re.sub(r'\s+','',code),literal_tokens(code)):code for code in verified_blocks}
    pattern=re.compile(r'Пример на слайде:\s*\n([^\n]*(?:\n(?!\n)[^\n]*)*)')
    def convert(match):
        fragment=match[1].strip('\n');before=text[max(0,match.start()-90):match.start()]
        context='результат' if re.search(r'(?:Результат|Вывод|Входные данные)\s*:\s*$',before,re.I) else ''
        restored=known.get((re.sub(r'\s+','',fragment),literal_tokens(fragment)),fragment)
        return '```'+program_kind(restored,context)+'\n'+restored+'\n```'
    text=pattern.sub(convert,text)
    parts=re.split(r'(```[\s\S]*?```)',text)
    for i in range(0,len(parts),2):parts[i]=re.sub(r'(?<![`\w])(print\(\)|input\(\)|int\(\)|float\(\)|len\(\)|sum\(\)|range\(\))(?!`)',r'`\1`',parts[i])
    text=''.join(parts)
    return text

def infer_topics(task,lesson_id):
    text=(task.get('statement','')+' '+(task.get('solution') or {}).get('code','')).lower()
    rules=[('input(',['input','conversion','types','variables']),('print(',['output']),('for ',['loops']),('while ',['loops']),('if ',['conditions','logic']),('def ',['functions']),('.csv',['csv','tables']),('dataframe',['tables']),('mean',['statistics']),('median',['statistics']),('std',['statistics']),('accuracy',['metrics']),('train_test_split',['split']),('classifier',['classification']),('regression',['regression']),('cluster',['clustering']),('признак',['features','target']),('проект',['problem','prototype','documentation'])]
    result=[]
    for marker,ids in rules:
        if marker in text:result.extend(ids)
    return list(dict.fromkeys(result))[:9]

def native_lecture(source,folder,lesson):
    original=source/'Архив iSmart'/folder/'Оригиналы'
    candidates=[]
    if original.exists():
        for p in original.glob('*.pdf'):
            if re.search(r'учител|преподав|инструкц|метод|ответ|вариант|ключ',p.name,re.I):continue
            candidates.append(p)
    # Canonical shared files are already associated through the lesson manifest.
    catalog=load(source/'Каталог оригиналов.json')
    for key,value in catalog.items():
        if folder.replace('/','\\')+'\\Оригиналы\\' in key and key.lower().endswith('.pdf') and not re.search(r'учител|преподав|инструкц|метод|ответ|вариант|ключ',key,re.I):
            p=source/value.replace('\\','/')
            if p.exists():candidates.append(p)
    return sorted(set(candidates),key=lambda p:(-p.stat().st_size,p.name))[0] if candidates else None

def original_lecture_html(metadata,pages):
    parts=[];elements=[]
    for link in metadata.get('links',[]):
        if not link.get('text','').endswith('Теория'):continue
        match=re.search('/element/([^?]+)',link.get('href',''))
        if not match or match[1] in elements or match[1] not in pages:continue
        capture=pages[match[1]];soup=BeautifulSoup(capture.get('html',''),'html.parser')
        main=soup.select_one('#course-article-pdf-source')
        if not main:continue
        for node in main.select('script,iframe,form,input,textarea,button,object,embed'):node.decompose()
        for node in main.find_all(True):
            for attr in list(node.attrs):
                if attr.lower().startswith('on'):del node.attrs[attr]
            if node.has_attr('href'):
                if re.search(r'/teacher/|[?&]back=',node['href']):del node.attrs['href']
        parts.append('<section class="original-lecture-part">'+str(main)+'</section>');elements.append(match[1])
    return '\n'.join(parts),elements

def project_reference(content,source,private,solutions_dir=None):
    content,source,private=map(Path,[content,source,private]);index=load(content/'index.json');source_index=load(private/'full-course-index.json') if (private/'full-course-index.json').exists() and len(index['lessons'])<82 else json.loads(json.dumps(index))
    private.mkdir(parents=True,exist_ok=True);dump(private/'full-course-index.json',source_index)
    snapshots=load(source/'Архив iSmart/Снимки страниц.json');captures=snapshots['courseCaptures']
    pages={re.search('/element/([^?]+)',c['url'])[1]:c for c in captures if c.get('kind')=='page' and '/element/' in c.get('url','')}
    approved={}
    if solutions_dir and Path(solutions_dir).exists():
        for p in sorted(Path(solutions_dir).glob('*.json')):
            for entry in load(p).get('solutions',[]):
                if entry['taskId'] in approved:raise ValueError('Duplicate reviewed solution: '+entry['taskId'])
                approved[entry['taskId']]=entry
    lessons=[];documents=[];removed=[];coverage=[]
    for row in index['lessons']:
        path=content/'lessons'/f"{row['id']}.json";lesson=load(path)
        if row['kind']=='control':path.unlink();removed.append(row['id']);continue
        folder=lesson['source']['path'];metadata=load(source/'Архив iSmart'/folder/'Состав исходников.json')
        official_order={re.search('/element/([^?]+)',link['href'])[1]:i for i,link in enumerate(metadata.get('links',[])) if '/element/' in link.get('href','') and not link.get('text','').endswith('Теория')}
        tasks=[]
        for task in lesson['tasks']:
            link=task.get('ismartLink');element=link.get('elementId') if link else None
            if row['kind']!='lesson' or task['origin']!='ismart' or element not in official_order:continue
            capture=pages.get(element)
            if capture:task['statement']=capture_markdown(capture);task['source']={'elementId':element,'archive':'Снимки страниц.json','sha256':digest(capture.get('html','').encode())}
            task['solution']=None;task['solutionStatus']='unreviewed'
            review=approved.get(task['id'])
            if review:
                if review.get('status')!='published' or review.get('rightsConfirmed') is not True or not review.get('reviewedAt') or not review.get('explanation'):raise ValueError('Unreviewed solution in publication manifest')
                value=review.get('code') or review.get('answer','')
                if digest(value.encode())!=review['sha256']:raise ValueError('Solution checksum mismatch: '+task['id'])
                evidence=review.get('verificationEvidence',{})
                if evidence.get('codeSha256')!=review['sha256']:raise ValueError('Verification evidence checksum mismatch')
                if review.get('testCount',0)!=len(review.get('tests',[])) or evidence.get('passed')!=evidence.get('total') or evidence.get('total')!=review.get('testCount',0):raise ValueError('Incomplete local verification evidence')
                if review.get('code'):ast.parse(review['code'])
                task['solution']={k:v for k,v in review.items() if k not in ['taskId','rightsConfirmed','reviewedAt','reviewer','sha256','verificationEvidence','tests']}
                task['solution']['id']=task['id']+'-S1';task['solutionStatus']='published'
            task['relatedTopics']=infer_topics(task,lesson['id'])
            if task['solution']:task['solution']['relatedTopics']=list(dict.fromkeys(task['solution'].get('relatedTopics',[])+task['relatedTopics']))
            tasks.append(task)
        tasks.sort(key=lambda t:official_order[t['ismartLink']['elementId']])
        # Platform numbers are authoritative. Supplemental subquestions remain distinct IDs.
        for i,task in enumerate(tasks,1):
            match=re.search(r'(?:Задание|Задача|Вопрос)\s*№?\s*(\d+)',task['ismartLink']['label'],re.I)
            task['number']=int(match[1]) if match else i
        lesson['tasks']=tasks;lesson.pop('practice',None);lesson['taskCount']=len(tasks)
        codes=[]
        corrected=source.parent/'iSmart - исправленный комплект'/folder/'Лекция по слайдам.md'
        if corrected.exists():codes.extend(re.findall(r'```(?:python|py)?\n([\s\S]*?)```',corrected.read_text(encoding='utf-8-sig')))
        for capture in pages.values():
            if capture.get('unitTitle')==lesson['originalTitle']:codes.extend(capture.get('codes',[]))
        from import_course import adapt_lecture
        raw_lecture=(source/folder/'Лекция по слайдам.md').read_text(encoding='utf-8-sig')
        lesson['lecture']=format_lecture(adapt_lecture(raw_lecture)[0],codes)
        lecture_source=source/folder/'Лекция по слайдам.md'
        original_pdf=native_lecture(source,folder,lesson)
        original_label=original_pdf.name if original_pdf else None
        if original_pdf:
            stable_original=private/'document-originals'/f"{lesson['id']}.pdf";stable_original.parent.mkdir(exist_ok=True);shutil.copyfile(original_pdf,stable_original);original_pdf=stable_original
        original_html,html_elements=original_lecture_html(metadata,pages)
        documents.append({'lessonId':lesson['id'],'title':lesson['title'],'originalPdf':str(original_pdf) if original_pdf else None,'originalPdfLabel':original_label,'originalHTML':original_html,'htmlElements':html_elements,'lectureMarkdown':str(lecture_source),'webLecture':lesson['lecture'],'originalMarkdown':format_lecture(lecture_source.read_text(encoding='utf-8-sig'),codes),'slidePaths':lesson['slides'],'sourcePresentation':str(next((source/folder).glob('Презентация*.pptx'))),'folder':folder})
        lesson['extendedTopics']=list(dict.fromkeys(topic for task in tasks for topic in task['relatedTopics']))
        paragraphs=[re.sub(r'[*`\n]+',' ',p).strip() for p in lesson['lecture'].split('\n\n') if not p.startswith(('#','-','|','```','Источник:')) and 70<len(p)<350 and 'Содержание' not in p]
        lesson['description']=paragraphs[0] if paragraphs else f"Лекция, презентация и справочные материалы занятия {lesson['number']}."
        extended=Path(__file__).resolve().parents[1]/'content/extended'/f"{lesson['id']}.md"
        if extended.exists():lesson['extendedLecture']=extended.read_text(encoding='utf-8')
        dump(path,lesson)
        summary={k:lesson[k] for k in row if k!='tasks'};summary['tasks']=[{k:task[k] for k in ['id','title','type','number','origin','solutionStatus']} for task in tasks];lessons.append(summary)
        for task in tasks:coverage.append({'module':lesson['moduleId'],'lessonId':lesson['id'],'lesson':lesson['number'],'taskId':task['id'],'title':task['title'],'type':task['type'],'published':bool(task['solution']),'verified':bool(task['solution'] and task['solution'].get('verification') in ['local','project_tests','ismart']),'explanation':bool(task['solution'] and task['solution'].get('explanation')),'verifiedIsmartLink':task['ismartLink']['status']=='verified','reason':None if task['solution'] else 'Нет индивидуально проверенного полного решения в манифесте публикации.'})
    index['lessons']=lessons
    for module in index['modules']:
        contained=[l for l in lessons if l['moduleId']==module['id']];module['lessonIds']=[l['id'] for l in contained];module['lessonCount']=len(contained);module['controlCount']=0;module['taskCount']=sum(l['taskCount'] for l in contained)
    index['counts']={**index['counts'],'sections':len(lessons),'controls':0,'additionalPractices':0,'tasks':len(coverage),'officialPracticalElements':len(coverage),'publishedSolutions':sum(t['published'] for t in coverage),'sourceSections':len(source_index['lessons'])}
    dump(content/'index.json',index);dump(private/'document-sources.json',documents)
    search=[]
    for row in lessons:
        lesson=load(content/'lessons'/f"{row['id']}.json")
        search.append({'id':row['id'],'title':row['title'],'context':'Занятие '+row['number'],'url':'/lesson/'+row['id'],'body':lesson['lecture']+' '+lesson.get('extendedLecture','')})
        for task in lesson['tasks']:search.append({'id':task['id'],'title':task['title'],'context':f"Занятие {row['number']} / Задание {task['number']}",'aliases':f"{row['number']} №{task['number']} задание {task['number']} занятие {row['number'].split('.')[-1]} "+' '.join(task['relatedTopics']),'url':f"/lesson/{row['id']}/task/{task['id']}",'body':task['statement']+' '+(task.get('solution') or {}).get('code','')})
    dump(content/'search-index.json',search)
    report=load(content/'import-report.json');report['sourceCounts']=report.get('sourceCounts',report['counts']);report['counts']=index['counts'];report['publication']['solutions']='381_individually_reviewed_ordinary_practice_answers_authorized'
    if not any(issue['lessonId']=='M02-L17' for issue in report['knownIssues']):report['knownIssues'].append({'lessonId':'M02-L17','message':'В исходном виджете задания 3.1 часть подписей диапазонов повреждена. Пропуски сохранены явно; ответ поясняет выбранные интервалы.'})
    report['manualReview']=['Проверить кандидаты ссылок в авторизованной студенческой сессии.','Веб-превью презентаций проверены по геометрии; попиксельная сверка с PowerPoint не заявляется.']
    report['projection']={'excludedControls':sorted(set(removed+[r['id'] for r in source_index['lessons'] if r['kind']=='control'])),'authorPractice':'excluded_from_public_files','ordinaryPracticeSolutionsPermission':'confirmed_by_owner_2026-11-02','assessmentKeys':'excluded','rawRegistry':'kept_private'}
    dump(content/'import-report.json',report)
    modules=[]
    for m in range(1,6):
        tasks=[t for t in coverage if t['module']==m]
        modules.append({'module':m,'officialTasks':len(tasks),'codeTasks':sum(t['type'] in ['code','debug','file'] for t in tasks),'textTasks':sum(t['type'] not in ['code','debug','file'] for t in tasks),'publishedSolutions':sum(t['published'] for t in tasks),'verifiedSolutions':sum(t['verified'] for t in tasks),'withoutSolutions':sum(not t['published'] for t in tasks),'withExplanations':sum(t['explanation'] for t in tasks),'verifiedIsmartLinks':sum(t['verifiedIsmartLink'] for t in tasks)})
    coverage_report={'modules':modules,'tasks':coverage,'total':len(coverage),'published':sum(t['published'] for t in coverage),'missingMaterials':report.get('missing',[]),'runtimeFixtures':sum(s.get('testCount',0) for s in approved.values()),'officialVerification':'not_performed_without_student_session'}
    dump(content/'solution-coverage.json',coverage_report)
    return coverage_report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--content',required=True,type=Path);p.add_argument('--source',required=True,type=Path);p.add_argument('--private-output',required=True,type=Path);p.add_argument('--solutions',type=Path)
    args=p.parse_args();result=project_reference(args.content,args.source,args.private_output,args.solutions);print(json.dumps({'officialTasks':result['total'],'published':result['published']},ensure_ascii=False))
