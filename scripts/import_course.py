"""Deterministic iSMART -> student-only web content. Never executes archive code.

Usage: python scripts/import_course.py --source <zip-or-directory> --private-output <outside-public-path>
"""
from __future__ import annotations
import argparse, collections, hashlib, html, json, re, shutil, tempfile, zipfile
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urlunsplit, unquote
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

PROJECT = Path(__file__).resolve().parents[1]
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main', 'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
MODULE_TITLES = [
    'Python, данные и алгоритмическое мышление для ИИ',
    'Математические основы искусственного интеллекта',
    'Алгоритмы и модели искусственного интеллекта',
    'Проектирование и защита учебного ИИ-проекта',
    'Итоговая аттестация',
]
DESCRIPTIONS = [
    'От первой программы к анализу данных. Освойте Python и научитесь мыслить алгоритмами.',
    'Функции, вероятность и статистика — понятный язык, на котором обучаются модели.',
    'Обучайте модели, оценивайте качество и решайте задачи классификации и регрессии.',
    'Пройдите путь от задачи пользователя до работающего прототипа и защиты решения.',
    'Представьте свой ИИ-проект, продемонстрируйте результат и объясните ограничения.',
]

def read(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')

def load(path: Path):
    return json.loads(read(path))

def dump(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_extract(source: Path, destination: Path):
    with zipfile.ZipFile(source) as z:
        for entry in z.infolist():
            target = (destination / entry.filename.replace('\\', '/')).resolve()
            if not target.is_relative_to(destination.resolve()) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe archive member')
        z.extractall(destination)

def stable_id(folder: str, module: int) -> str:
    match = re.search(r'Занятие (\d+)', folder)
    if match:
        return f'M{module:02d}-L{int(match[1]):02d}'
    if 'Итоговая' in folder:
        return f'M{module:02d}-L01'
    return f'M{module:02d}-C' + re.search(r'Контроль (.+)', folder)[1]

def clean_title(title: str) -> str:
    title = re.sub(r'^Тема \d+\.\s*', '', title)
    return re.sub(r'^Занятие [\d.]+\.?\s*', '', title).strip().rstrip('.')

def student_url(url: str) -> str | None:
    """Only an observed course URL, stripped of teacher return parameters; still UNVERIFIED."""
    u = urlsplit(url)
    if u.netloc not in ('', 'edu.future.ismart.org') or not re.fullmatch(r'/course/practice/\d+/unit/[a-zA-Z0-9]+/element/[a-zA-Z0-9]+', u.path):
        return None
    return urlunsplit(('https', 'edu.future.ismart.org', u.path, '', ''))

def redact_links(text: str) -> str:
    # Do not expose archive-relative paths, teacher URLs, return parameters or credentials.
    text = re.sub(r'^.*(?:Источник:|Текст преподавателя\.|ГОВОРИМ СТУДЕНТАМ).*$', '', text, flags=re.M)
    text = re.sub(r'https?://[^\s)<>]+', lambda m: m[0] if '/teacher/' not in unquote(m[0]) and not re.search(r'(?:token|auth|session|back)=', m[0], re.I) else '[служебная ссылка исключена]', text)
    text = re.sub(r'\[([^\]]+)\]\((?!https://|#)[^)]+\)', r'\1', text)
    return text.strip()

def adapt_lecture(text: str) -> tuple[str, list[str]]:
    text = redact_links(text)
    changes = ['Удалены служебные адреса, инструкция для преподавателя и метки речи; обращения к слайду адаптированы. Оригинал сохранён отдельно.']
    for a, b in [('Посмотрите на слайд. ', ''), ('Обратите внимание на слайд. ', ''), ('Посмотрите на слайд: ', ''), ('Сегодня мы разбираем тему', 'В этом занятии рассматривается тема')]:
        text = text.replace(a, b)
    return re.sub(r'\n{4,}', '\n\n', text), changes

class MarkdownHTML(HTMLParser):
    """Allowlist HTML -> Markdown, dropping active content and all input attributes."""
    BLOCK = {'p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'table', 'tr'}
    DROP = {'script', 'style', 'iframe', 'object', 'embed', 'svg', 'form', 'button', 'input', 'textarea'}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.drop = 0; self.pre = 0
    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            if tag not in {'input', 'embed'}: self.drop += 1
            return
        if self.drop: return
        if tag == 'pre': self.pre += 1; self.out.append('\n\n```\n')
        elif tag == 'br': self.out.append('\n')
        elif tag in self.BLOCK: self.out.append('\n\n' + ('#' * int(tag[1]) + ' ' if re.match('h[1-4]', tag) else ''))
        elif tag == 'li': self.out.append('\n- ')
        elif tag in {'td', 'th'}: self.out.append(' | ')
        elif tag in {'strong', 'b'}: self.out.append('**')
        elif tag in {'em', 'i'}: self.out.append('*')
    def handle_endtag(self, tag):
        if tag in self.DROP:
            if tag not in {'input', 'embed'}: self.drop = max(0, self.drop - 1)
            return
        if self.drop: return
        if tag == 'pre': self.out.append('\n```\n\n'); self.pre = max(0, self.pre-1)
        elif tag in self.BLOCK: self.out.append('\n\n')
        elif tag in {'strong', 'b'}: self.out.append('**')
        elif tag in {'em', 'i'}: self.out.append('*')
    def handle_data(self, data):
        if not self.drop: self.out.append(data)
    def markdown(self, data: str) -> str:
        self.feed(data)
        return re.sub(r'\n{3,}', '\n\n', ''.join(self.out)).strip()

def source_body(capture: dict) -> str:
    """Capture contains app chrome; take the semantic article when present."""
    raw = capture.get('html', '')
    match = re.search(r'<article\b[^>]*>([\s\S]*?)</article>', raw)
    if match:
        body = MarkdownHTML().markdown(match[1])
    else:
        # Prepared pages provide actual content; fallback uses captured text after app chrome.
        body = capture.get('text', '')
        for marker in ['Скачать PDF\n', 'Консоль\n']:
            if marker in body: body = body.split(marker, 1)[1]; break
        body = re.sub(r'^.*(?:Материалы для учителя|Запустить тесты|Описание|^Тесты$).*$', '', body, flags=re.M)
    return redact_links(body)

def attr(node, name, default=''):
    return node.get(name, default) if node is not None else default

def color(node, default='none'):
    if node is None: return default
    c = node.find('a:srgbClr', NS)
    return '#' + c.get('val') if c is not None else default

def text_svg(tx, x, y, w, h):
    """Render DrawingML rich text in a fixed-size XHTML box inside a script-free SVG."""
    if tx is None: return ''
    bp = tx.find('a:bodyPr', NS)
    margins = [float(attr(bp, key, '0')) / 9525 for key in ['tIns','rIns','bIns','lIns']]
    paragraphs = []
    default = tx.find('a:lstStyle/a:defPPr/a:defRPr', NS)
    for p in tx.findall('a:p', NS):
        pp = p.find('a:pPr', NS); dp = pp.find('a:defRPr', NS) if pp is not None else default
        if dp is None: dp = default
        spans = []
        for run in list(p):
            if run.tag.endswith('}br'): spans.append('<br/>'); continue
            if not run.tag.endswith(('}r', '}fld')): continue
            rp = run.find('a:rPr', NS)
            if rp is None: rp = dp
            size = float(attr(rp, 'sz', attr(dp, 'sz', '1800'))) / 100 * 96/72
            font = rp.find('a:latin', NS) if rp is not None else None
            face = attr(font, 'typeface', 'Arial')
            if face not in ('Arial', 'Consolas', 'Calibri', 'Courier New'): face = 'Arial'
            clr = color(rp.find('a:solidFill', NS) if rp is not None else None, color(dp.find('a:solidFill', NS) if dp is not None else None, '#172c43'))
            bold = '700' if attr(rp,'b',attr(dp,'b','0')) == '1' else '400'
            italic = 'italic' if attr(rp,'i','0') == '1' else 'normal'
            txt = html.escape(''.join(run.itertext()))
            spans.append(f'<span style="font-family:{face},sans-serif;font-size:{size:.3f}px;font-weight:{bold};font-style:{italic};color:{clr}">{txt}</span>')
        if not spans: spans = ['<br/>']
        align = {'ctr':'center','r':'right','just':'justify'}.get(attr(pp,'algn'), 'left')
        before = pp.find('a:spcBef/a:spcPts',NS) if pp is not None else None
        after = pp.find('a:spcAft/a:spcPts',NS) if pp is not None else None
        mt = float(attr(before,'val','0'))/100*96/72; mb = float(attr(after,'val','0'))/100*96/72
        paragraphs.append(f'<p style="margin:{mt:.2f}px 0 {mb:.2f}px;line-height:1.12;text-align:{align};white-space:pre-wrap;overflow-wrap:break-word">' + ''.join(spans) + '</p>')
    justify = {'ctr':'center','b':'flex-end'}.get(attr(bp,'anchor'), 'flex-start')
    pad = ' '.join(f'{m:.2f}px' for m in margins)
    return f'<foreignObject x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"><div xmlns="http://www.w3.org/1999/xhtml" style="box-sizing:border-box;width:100%;height:100%;padding:{pad};display:flex;flex-direction:column;justify-content:{justify};overflow:hidden">' + ''.join(paragraphs) + '</div></foreignObject>'

def render_deck(pptx: Path, out: Path) -> tuple[list[str], list[str]]:
    warnings = []; slides = []
    with zipfile.ZipFile(pptx) as z:
        pres = ET.fromstring(z.read('ppt/presentation.xml')); size = pres.find('p:sldSz', NS)
        width = float(size.get('cx'))/9525; height = float(size.get('cy'))/9525
        names = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)), key=lambda n:int(re.search(r'(\d+)\.xml',n)[1]))
        for i, name in enumerate(names,1):
            root = ET.fromstring(z.read(name)); bits = []
            bg = root.find('p:cSld/p:bg/p:bgPr/a:solidFill',NS)
            bits.append(f'<rect width="{width}" height="{height}" fill="{color(bg,"#ffffff")}"/>')
            for shape in root.find('p:cSld/p:spTree',NS):
                kind = shape.tag.split('}')[-1]
                if kind in ['nvGrpSpPr','grpSpPr']: continue
                if kind not in ['sp','graphicFrame']:
                    warnings.append(f'{pptx.parent.name} slide {i}: unsupported {kind}'); continue
                xf = shape.find('p:spPr/a:xfrm',NS) if kind == 'sp' else shape.find('p:xfrm',NS)
                if xf is None: continue
                off=xf.find('a:off',NS); ext=xf.find('a:ext',NS)
                x,y,w,h=[float(attr(n,k,'0'))/9525 for n,k in [(off,'x'),(off,'y'),(ext,'cx'),(ext,'cy')]]
                if kind == 'sp':
                    sp=shape.find('p:spPr',NS); fill=color(sp.find('a:solidFill',NS)); ln=sp.find('a:ln',NS)
                    stroke=color(ln.find('a:solidFill',NS) if ln is not None else None)
                    stroke_width=float(attr(ln,'w','0'))/9525
                    bits.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
                    bits.append(text_svg(shape.find('p:txBody',NS),x,y,w,h))
                else:
                    table=shape.find('a:graphic/a:graphicData/a:tbl',NS)
                    if table is None: warnings.append(f'{name}: unsupported graphic');continue
                    cols=[float(c.get('w'))/9525 for c in table.findall('a:tblGrid/a:gridCol',NS)]
                    cy=y
                    for row in table.findall('a:tr',NS):
                        rh=float(row.get('h'))/9525;cx=x
                        for j,cell in enumerate(row.findall('a:tc',NS)):
                            cw=cols[j];pr=cell.find('a:tcPr',NS);cf=color(pr.find('a:solidFill',NS) if pr is not None else None,'#ffffff')
                            bits.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{rh}" fill="{cf}" stroke="#dce5ea" stroke-width="0.7"/>')
                            bits.append(text_svg(cell.find('a:txBody',NS),cx+5,cy+4,max(1,cw-10),max(1,rh-8)));cx+=cw
                        cy+=rh
            svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Слайд {i}">' + ''.join(bits) + '</svg>'
            target=out/f'{i:03d}.svg';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(svg,encoding='utf-8');slides.append(target.name)
    return slides,warnings

def student_pptx(source: Path, target: Path):
    """Derivative only. Original remains unchanged. Remove notes, comments and personal metadata."""
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source) as zi, zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            if info.filename.startswith(('ppt/notesSlides/','ppt/notesMasters/','ppt/comments/','ppt/commentAuthors','docProps/')): continue
            data=zi.read(info.filename)
            if info.filename.endswith('.rels') or info.filename=='[Content_Types].xml':
                t=ET.fromstring(data)
                for el in list(t):
                    if any(x in str(el.attrib) for x in ['notesSlide','notesMaster','comment','docProps']):t.remove(el)
                data=ET.tostring(t,encoding='utf-8',xml_declaration=True)
            zi2=zipfile.ZipInfo(info.filename,date_time=(2026,1,1,0,0,0));zi2.compress_type=zipfile.ZIP_DEFLATED;zo.writestr(zi2,data)

def practice_sections(text: str) -> list[tuple[str,str]]:
    # Top-level sections of the already curated student practice. Nested titles belong to their task.
    starts=list(re.finditer(r'^#{2,3} (.+)$',text,re.M));result=[]
    for i,m in enumerate(starts):
        heading=m[1].strip()
        if not (re.match(r'(?:(?:Задание|Вопрос)\s*(?:№|\d|итогового)|Авторск|Дополнительн|Практическ|Самостоятельн)',heading,re.I)):continue
        end=len(text)
        for n in starts[i+1:]:
            if re.match(r'(?:(?:Задание|Вопрос)\s*(?:№|\d|итогового)|Таблицы из|Авторск|Дополнительн|Практическ|Самостоятельн)',n[1],re.I):end=n.start();break
        # "Задание №2" followed by "Задание 2. ..." is one section, not two.
        body=text[m.end():end].strip()
        if not body:continue
        if re.fullmatch(r'Задание №?\d+',heading) and result and result[-1][1]==body:continue
        result.append((heading,body))
    return result

def task_type(title, body, codes, assessment=False, official_kind=''):
    if assessment:return 'assessment'
    t=(title+' '+body).lower()
    if 'исправ' in title.lower() or 'исправьте программу' in t or 'ошибочн' in title.lower():return 'debug'
    if any(x in t for x in ['.csv','.ipynb']):return 'file'
    if official_kind=='Вопрос':return 'choice'
    if 'Свободный ответ' in official_kind:return 'free_response'
    if official_kind=='Практика':return 'code'
    if re.search(r'выберите (?:один|правильн|верн)|вариант[ыа]? ответ|что выведет',t):return 'choice'
    if 'проект' in title.lower():return 'project'
    if codes or '```' in body:return 'code'
    return 'free_response'

def build(source: Path, private: Path, approvals: Path | None = None, rights_confirmed: bool = False):
    if private.resolve().is_relative_to(PROJECT.resolve()):
        raise ValueError('Private output must be outside the distributable project.')
    rights_status='public_distribution_confirmed' if rights_confirmed else 'private_owner_use'
    with tempfile.TemporaryDirectory(prefix='cfa-import-') as tmp:
        if source.is_file():
            extracted=Path(tmp)/'archive';extracted.mkdir();safe_extract(source,extracted);bases=list(extracted.rglob('Состав комплекта.json'))
        else:bases=list(source.rglob('Состав комплекта.json'))
        if len(bases)!=1:raise ValueError('Expected one Состав комплекта.json')
        root=bases[0].parent;manifest=load(bases[0]);verification=load(root/'Проверка комплекта.json')
        # Read all required audit documents before deriving pages.
        required=['Прочитать перед использованием.md','Примечания преподавателю.md','Каталог оригиналов.json','Архив iSmart/Реестр курса.md','Архив iSmart/Все ссылки.json','Архив iSmart/Снимки страниц.json','Архив iSmart/Состояние подготовки.json']
        documents={name:read(root/name) for name in required}
        snapshots=json.loads(documents['Архив iSmart/Снимки страниц.json']);captures=snapshots['courseCaptures']
        original_catalog=json.loads(documents['Каталог оригиналов.json'])
        stage=Path(tmp)/'content';stage.mkdir();private.mkdir(parents=True,exist_ok=True)
        rows=[];private_lessons=[];warnings=[];hashes=collections.defaultdict(list);slide_count=0;file_count=0;task_count=0;link_count=0;official_count=0
        approved=load(approvals) if approvals else {'solutions':[]}
        for order,row in enumerate(manifest):
            folder=row['folder'].replace('\\','/');prepared=root/folder;original=root/'Архив iSmart'/folder
            metadata=load(original/'Состав исходников.json');lid=stable_id(folder,row['module'])
            assessment='Контроль' in folder or 'аттестаци' in row['title'].lower()
            lesson_kind='control' if 'Контроль' in folder else 'final' if row['module']==5 else 'assessment' if assessment else 'lesson'
            lecture_path=prepared/'Лекция по слайдам.md';practice_path=prepared/'Практика для студентов.md'
            lecture,changes=adapt_lecture(read(lecture_path)) if lecture_path.exists() else ('',[])
            practice=redact_links(read(practice_path)) if practice_path.exists() else ''
            matched=[c for c in captures if c.get('kind')=='page' and c.get('unitTitle')==row['title'] and int(c.get('module',0))==int(row['module'])]
            page_by_element={re.search(r'/element/([^?]+)',c.get('url',''))[1]:c for c in matched if '/element/' in c.get('url','')}
            links=[]
            for l in metadata.get('links',[]):
                candidate=student_url(l.get('href',''));url=l.get('href','');q=parse_qs(urlsplit(url).query)
                unit_match=re.search(r'/unit/([^/]+)',url);element_match=re.search(r'/element/([^?]+)',url)
                links.append({'id':element_match[1] if element_match else sha(url.encode())[:16],'label':l.get('text','').split('\n')[0], 'kind':l.get('text','').strip().split('\n')[-1], 'candidateUrl':candidate,'status':'unverified','unitId':unit_match[1] if unit_match else None,'elementId':element_match[1] if element_match else None})
            link_count+=len(links)
            tasks=[];sections=practice_sections(practice)
            official_links=[l for l,orig in zip(links,metadata.get('links',[])) if 'Теория' not in orig.get('text','')]
            # Prefer exact numbered headings in the curated practice; captured fallback only for missing sections.
            seen_numbers=set()
            for position,(heading,body) in enumerate(sections):
                n=re.search(r'(Задание|Вопрос)\s*№?\s*(\d+)',heading,re.I);number=int(n[2]) if n else position+1
                number_key=(n[1].lower(),number) if n else ('other',number)
                if n and number_key in seen_numbers:continue
                seen_numbers.add(number_key)
                norm=lambda s:re.sub(r'[^\w]','',s.lower())
                candidate=next((l for l in official_links if norm(l['label'])==norm(heading)),None)
                if candidate is None and n:
                    possible=[l for l in official_links if re.search(n[1]+r'\s*№?\s*'+str(number)+r'(?:\D|$)',l['label'],re.I)]
                    if len(possible)==1:candidate=possible[0]
                if not candidate and len(sections)==len(official_links):candidate=official_links[position]
                origin='author' if re.search(r'авторск|дополнительн',heading,re.I) or (re.search(r'авторск|не оригинальные задания',practice,re.I) and not official_links) else 'ismart'
                tid='T-'+candidate['elementId'] if candidate and candidate['elementId'] else f'{lid}-A{number:02d}'
                c=page_by_element.get(candidate['elementId'],{}) if candidate else {}
                codes=re.findall(r'```[^\n]*\n([\s\S]*?)```',body)
                detail_title=re.search(r'^###?\s+(Задание\s+\d+\.\s*.+)$',body,re.M)
                title=detail_title[1] if detail_title else heading
                task={'id':tid,'number':number,'title':title,'type':task_type(title,body,codes,assessment,candidate.get('kind','') if candidate else ''),'moduleId':row['module'],'lessonId':lid,'statement':body,'origin':origin,'ismartLink':candidate,'files':[],'variants':[],'solution':None,'solutionStatus':'teacher_only' if assessment else 'unreviewed','source':{'path':folder+'/Практика для студентов.md','sha256':sha(practice_path.read_bytes())},'publication':{'audience':'student','rights':rights_status,'status':'published'}}
                tasks.append(task)
            # Retain every official practical element even when curated practice uses nonstandard headings.
            task_link_ids={t['ismartLink']['elementId'] for t in tasks if t['ismartLink']}
            for link in official_links:
                if link['elementId'] in task_link_ids:continue
                c=page_by_element.get(link['elementId'],{});body=source_body(c) if not assessment else 'Официальный контроль проходит на iSMART. Условия и правила смотрите в студенческой практике занятия. Варианты и ключи из преподавательского архива не опубликованы.'
                if not body:body='Условие этого элемента не сохранено отдельно. Изучите практику занятия и найдите элемент на официальной платформе.';warnings.append({'lessonId':lid,'message':'Нет отдельного условия: '+link['label']})
                tid='T-'+link['elementId']
                tasks.append({'id':tid,'number':len(tasks)+1,'title':link['label'],'type':task_type(link['label'],body,c.get('codes',[]),assessment,link.get('kind','')),'moduleId':row['module'],'lessonId':lid,'statement':body,'origin':'ismart','ismartLink':link,'files':[],'variants':[],'solution':None,'solutionStatus':'teacher_only' if assessment else 'unreviewed','source':{'path':folder+'/Страницы','elementId':link['elementId']},'publication':{'audience':'student','rights':rights_status,'status':'published'}})
            # Explicit solution approvals are bound to lesson/task and exact reviewed code digest.
            for approval in approved.get('solutions',[]):
                if approval.get('lessonId')!=lid:continue
                task=next((t for t in tasks if t['id']==approval.get('taskId')),None)
                if not task:raise ValueError('Approved solution task not found')
                if assessment or lesson_kind=='final' or approval.get('status')!='approved' or approval.get('rightsConfirmed') is not True or not approval.get('reviewer') or not approval.get('reviewedAt'):raise ValueError('Cannot publish restricted or unapproved solution')
                verification=approval.get('verification','source')
                if verification not in {'source','local','project_tests','ismart'}:raise ValueError('Invalid verification status')
                if verification!='source' and not approval.get('verificationEvidence'):raise ValueError('Verification evidence is required')
                code=approval['code']
                if sha(code.encode())!=approval.get('sha256'):raise ValueError('Reviewed solution digest mismatch')
                task['solution']={'id':task['id']+'-S1','code':code,'explanation':approval.get('explanation',''),'verification':verification,'status':'published','source':approval.get('source','reviewed publication manifest')};task['solutionStatus']='published'
            decks=sorted(prepared.glob('Презентация*.pptx'));slides=[];deck_download=None
            if decks:
                deck=decks[0];slides,sw=render_deck(deck,stage/'slides'/lid);warnings.extend({'lessonId':lid,'message':w} for w in sw);slide_count+=len(slides)
                deck_download=f'/content/files/{lid}-student.pptx';student_pptx(deck,stage/'files'/f'{lid}-student.pptx')
                if len(slides)!=row['slides']:warnings.append({'lessonId':lid,'message':f"Реестр: {row['slides']} слайдов, фактически {len(slides)}"})
            files=[]
            for attachment in metadata.get('attachments',[]):
                rel=attachment.get('path','').replace('\\','/');catalog_key=('Архив iSmart/'+folder+'/Оригиналы/'+Path(rel).name).replace('/','\\');mapped=original_catalog.get(catalog_key) or original_catalog.get('Архив iSmart\\'+rel.replace('/','\\')) or original_catalog.get(rel.replace('/','\\'))
                p=root/mapped.replace('\\','/') if mapped else root/'Архив iSmart'/rel
                if not p.resolve().is_relative_to(root.resolve()) or not p.exists():
                    found=list((root/'Архив iSmart').rglob(Path(rel).name));p=found[0] if found else p
                suffix=p.suffix.lower();name=attachment.get('original_name',p.name)
                # Explicit student file allowlist; no DOCX, archive, hidden notes, assessment variants or keys.
                if suffix not in {'.csv','.ipynb','.pdf','.json'} or assessment or re.search(r'учител|преподав|method|ключ|ответ|answer|expected|solution|keys|эталон',name,re.I):continue
                if not p.resolve().is_relative_to(root.resolve()) or not p.exists():warnings.append({'lessonId':lid,'message':'Не найден файл '+name});continue
                data=p.read_bytes();digest=sha(data);hashes[digest].append(str(p.relative_to(root)));file_id=digest[:16]+suffix
                if suffix=='.ipynb':
                    notebook=json.loads(data);notebook['metadata']={}
                    for cell in notebook.get('cells',[]):
                        cell['metadata']={}
                        if cell.get('cell_type')=='code':cell['outputs']=[];cell['execution_count']=None
                    data=(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n').encode()
                target=stage/'files'/file_id;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                preview=None
                if suffix=='.csv':
                    import csv,io
                    try:
                        decoded=data.decode('utf-8-sig');dialect=csv.Sniffer().sniff(decoded[:4000]);reader=csv.reader(io.StringIO(decoded),dialect);preview=[]
                        for i,cells in enumerate(reader):
                            if i>=11:break
                            preview.append(cells)
                    except (UnicodeError,csv.Error):pass
                files.append({'id':file_id,'name':name,'type':suffix[1:],'url':'/content/files/'+file_id,'bytes':len(data),'sha256':sha(data),'sourceSha256':digest,'preview':preview,'derived':suffix=='.ipynb'})
                file_count+=1
            for task in tasks:task['files']=[f['id'] for f in files]
            task_count+=len(tasks);official_count+=len(official_links)
            theory=[]
            for link,raw in zip(links,metadata.get('links',[])):
                if 'Теория' not in raw.get('text','') or 'Инструкция' in link['label']:continue
                c=page_by_element.get(link['elementId'],{});body=source_body(c)
                if body:theory.append({'title':link['label'],'content':body,'source':{'elementId':link['elementId']}})
            summary={'id':lid,'moduleId':int(row['module']),'order':order,'number':'5.1' if row['module']==5 else str(row['module'])+'.'+(str(int(re.search(r'Занятие (\d+)',folder)[1])) if 'Занятие' in folder else 'К'+folder.split('Контроль ')[-1]),'title':clean_title(row['title']),'originalTitle':row['title'],'kind':lesson_kind,'taskCount':len(tasks),'slideCount':len(slides),'fileCount':len(files),'hasLecture':bool(lecture),'description':re.sub(r'[#*`\n]',' ',lecture.split('###')[1] if '###' in lecture else practice[:220])[:170].strip(),'tags':[], 'tasks':[{'id':t['id'],'title':t['title'],'type':t['type'],'number':t['number'],'origin':t['origin'],'solutionStatus':t['solutionStatus']} for t in tasks]}
            dump(stage/'lessons'/f'{lid}.json',{**summary,'lecture':lecture,'lectureChanges':changes,'practice':practice,'theory':theory,'tasks':tasks,'slides':[f'/content/slides/{lid}/{s}' for s in slides],'deckDownload':deck_download,'files':files,'ismartLinks':links,'source':{'path':folder,'archive':'ismart_course_unpacked.zip'},'publication':{'audience':'student','rights':rights_status,'status':'published'}})
            rows.append(summary)
            private_lessons.append({'id':lid,'metadata':metadata,'sourceFolder':folder,'teacherMaterials':[str(p.relative_to(root)) for p in prepared.glob('*') if 'преподавател' in p.name or 'Разбор' in p.name],'variants':row['variants'],'review':'required'})
        # All private source data and teacher links are written ONLY outside the deployable project.
        dump(private/'teacher-index.json',private_lessons)
        (private/'source-notes.md').write_text(documents['Примечания преподавателю.md'],encoding='utf-8')
        known_issues=[{'lessonId':'M01-L03','message':'Задание 2: вариант 15 из 20 даёт 75.0%. Задание 5: сдаётся перевод минут в секунды, пример метров — только демонстрация.'},{'lessonId':'M02-L12','message':'Выборочное и генеральное стандартное отклонение различаются: stdev и pstdev нельзя подменять.'},{'lessonId':'M02-L15','message':'В учебной функции пропущено двоеточие. Условие с or соответствует требованию; замена на and меняет задачу.'},{'lessonId':'M03-L16','message':'Занятия 3.16 и 3.17 — отдельные элементы с одинаковым названием.'}]
        counts={'modules':len(set(r['moduleId'] for r in rows)),'sections':len(rows),'lessons':sum(r['kind']!='control' for r in rows),'controls':sum(r['kind']=='control' for r in rows),'presentations':sum(bool(r['slideCount']) for r in rows),'slides':slide_count,'lectures':sum(r['hasLecture'] for r in rows),'tasks':task_count,'officialPracticalElements':official_count,'dataFiles':sum(f.suffix in {'.csv','.ipynb'} for f in (stage/'files').glob('*')),'fileBindings':file_count,'linksMapped':link_count,'verifiedStudentLinks':0,'teacherSections':sum(r['metadata'].get('teacher_saved') is True for r in private_lessons),'sourcePages':sum(c.get('kind')=='page' for c in captures),'variantViews':sum(c.get('kind')=='variant' for c in captures),'additionalPractices':len(list(root.glob('Модуль */*/Разбор дополнительной практики.md'))),'attachmentUrls':len({a.get('url') for row in private_lessons for a in row['metadata'].get('attachments',[]) if a.get('url')})}
        # One extra document (README.md for 1.16) is linked in captured HTML, but absent
        # from lesson attachment metadata and from the saved files. Exclude UI artwork.
        from urllib.parse import unquote
        metadata_urls={unquote(a['url']) for row in private_lessons for a in row['metadata'].get('attachments',[]) if a.get('url')}
        discovered_urls=set(metadata_urls)
        for capture in captures:
            for url in re.findall(r'(?:href|src)="(https://files-cdn\.ismart\.org/documents/[^"]+)"',capture.get('html','')):
                decoded=unquote(html.unescape(url));discovered_urls.add(decoded)
                if decoded not in metadata_urls:
                    warning={'lessonId':'M01-L16','message':'Сохранена ссылка на '+Path(urlsplit(decoded).path).name+', но файл отсутствует в комплекте и метаданных занятия.'}
                    if warning not in warnings:warnings.append(warning)
        counts['attachmentMetadataUrls']=counts['attachmentUrls'];counts['attachmentUrls']=len(discovered_urls)
        expected_map={'sections':'sections','presentations':'presentations','slides':'slides','lectures':'lectures','sourcePages':'source_pages','variantViews':'variant_page_views','teacherSections':'teacher_sections','additionalPractices':'additional_practices','attachmentUrls':'original_attachment_urls'}
        discrepancies=[{'metric':k,'expected':verification[v],'actual':counts[k]} for k,v in expected_map.items() if counts[k]!=verification[v]]
        report={'sourceName':source.name,'sourceSha256':sha(source.read_bytes()) if source.is_file() else None,'sourceDate':verification.get('date'),'counts':counts,'expected':verification,'discrepancies':discrepancies,'unboundAttachmentUrls':sorted(discovered_urls-metadata_urls),'warnings':warnings,'knownIssues':known_issues,'duplicates':[{'sha256':k,'paths':sorted(set(v))} for k,v in hashes.items() if len(set(v))>1],'missing':[{'lessonId':r['id'],'material':'lecture'} for r in rows if r['kind']!='control' and not r['hasLecture']]+[{'lessonId':'M01-L16','material':Path(urlsplit(u).path).name} for u in sorted(discovered_urls-metadata_urls)],'publication':{'audience':'public' if rights_confirmed else 'owner_private','studentMaterials':rights_status,'teacherMaterials':'excluded_from_public_build','solutions':'explicit_review_and_rights_confirmation_required','ismartLinks':'all_unverified_no_student_session','pptx':'notes_comments_and_personal_metadata_removed','originals':'unchanged_outside_project','publicRightsConfirmed':rights_confirmed},'manualReview':([] if rights_confirmed else ['Подтвердить права iSMART перед открытой публикацией.'])+['Проверить кандидаты ссылок в авторизованной студенческой сессии.','Рассмотреть решения по одному; контрольные ключи и варианты остаются закрытыми.','Сверить отрисовку всех слайдов с PowerPoint перед публичным выпуском.']}
        modules=[{'id':i,'title':MODULE_TITLES[i-1],'description':DESCRIPTIONS[i-1],'lessonIds':[r['id'] for r in rows if r['moduleId']==i],'lessonCount':sum(r['moduleId']==i and r['kind']!='control' for r in rows),'controlCount':sum(r['moduleId']==i and r['kind']=='control' for r in rows),'taskCount':sum(r['taskCount'] for r in rows if r['moduleId']==i)} for i in range(1,6)]
        dump(stage/'index.json',{'course':{'id':'ismart-spo-intelligent-solutions','title':'Разработчик интеллектуальных решений','subtitle':'Базовый уровень для студентов СПО · Код будущего','officialUrl':'https://edu.future.ismart.org/'},'modules':modules,'lessons':rows,'counts':counts})
        search=[]
        for r in rows:
            lesson=load(stage/'lessons'/f"{r['id']}.json")
            search.append({'id':r['id'],'title':r['title'],'context':'Занятие '+r['number'],'url':'/lesson/'+r['id'],'body':lesson['lecture']+' '+lesson['practice']+' '.join(t['content'] for t in lesson['theory'])})
            search.extend({'id':t['id'],'title':t['title'],'context':'Практика · '+r['number'],'url':f"/lesson/{r['id']}/task/{t['id']}",'body':t['statement']} for t in lesson['tasks'])
        dump(stage/'search-index.json',search)
        dump(stage/'import-report.json',report);dump(private/'import-report-full.json',report)
        from reference_content import project_reference
        project_reference(stage, root, private, PROJECT/'content/solutions')
        destination=PROJECT/'public/content'
        if destination.exists():
            if destination.is_symlink() or destination.resolve().parent!=(PROJECT/'public').resolve():raise ValueError('Unsafe output directory')
            shutil.rmtree(destination)
        shutil.copytree(stage,destination)
        import subprocess
        subprocess.run([__import__('sys').executable,'scripts/build-project-example.py'],cwd=PROJECT,check=True)
        subprocess.run(['node','scripts/fit-slides.mjs'],cwd=PROJECT,check=True)
        subprocess.run(['node','scripts/build-documents.mjs','--sources',str(private/'document-sources.json')],cwd=PROJECT,check=True)
        print(json.dumps({'counts':counts,'discrepancies':discrepancies,'warnings':len(warnings),'contentSha256':sha((destination/'index.json').read_bytes())},ensure_ascii=False))
        return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--private-output',type=Path,required=True);parser.add_argument('--publication-review',type=Path);parser.add_argument('--rights-confirmed',action='store_true',help='Owner explicitly confirmed public distribution rights')
    args=parser.parse_args();build(args.source,args.private_output,args.publication_review,args.rights_confirmed)
