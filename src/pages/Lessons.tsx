import {useEffect,useState} from 'react';
import {Link,Navigate,useParams,useSearchParams} from 'react-router-dom';
import {ArrowLeft,ArrowRight,BookOpen,Bookmark,ChevronDown,ChevronRight,Code2,FileText,FolderOpen,Presentation} from 'lucide-react';
import type {Lesson,Task} from '../models';
import {getLesson,assetUrl} from '../data';
import {useStore} from '../state';
import {CodeBlock,Files,Markdown,Notice,OfficialLink,TextAnswer,slug} from '../components/Content';
import {DocumentReader} from '../components/DocumentReader';
import {buildExtendedLecture} from '../extended';
import {topics} from '../learning';

export const taskLabels:Record<string,string>={code:'Программа Python',debug:'Исправление кода',file:'Работа с данными',choice:'Вопрос с вариантами',free_response:'Текстовый ответ',assessment:'Аттестация',project:'Образец проекта'};

function useLesson(id:string){
  const [lesson,setLesson]=useState<Lesson|null>(null);const [error,setError]=useState('');const {visit}=useStore();
  useEffect(()=>{
    setLesson(null);setError('');const controller=new AbortController();
    getLesson(id,controller.signal).then(result=>{if(!controller.signal.aborted){setLesson(result);visit(id)}}).catch(()=>{if(!controller.signal.aborted)setError('Материал не загрузился. Обновите страницу или вернитесь к каталогу.')});
    return()=>controller.abort();
  },[id]);
  return {lesson,error};
}

export function Loading(){return <div className="page loading"><div className="loader"/><p>Открываем материалы…</p></div>}
export function NotFound({message='Такой страницы нет в библиотеке.'}:{message?:string}){return <div className="page empty-page"><BookOpen size={35}/><h1>Материал не найден</h1><p>{message}</p><Link className="button" to="/catalog">Каталог занятий<ArrowRight size={17}/></Link></div>}

export function TaskList({lesson}:{lesson:Lesson}){
  return <div className="task-list">{lesson.tasks.map(task=><Link className="task-card" key={task.id} to={`/lesson/${lesson.id}/task/${task.id}`}><span className="task-list-number">{String(task.number).padStart(2,'0')}</span><div className="task-card-main"><strong>{task.title}</strong><span>{taskLabels[task.type]}{task.solutionStatus==='published'?' · Есть готовый ответ':''}</span></div><ArrowRight size={19}/></Link>)}</div>;
}

export function RelatedTopics({lessonId,ids}:{lessonId:string;ids?:string[]}){
  const related=topics.filter(topic=>ids?.length?ids.includes(topic.id):topic.lessons.includes(lessonId));
  if(!related.length)return null;
  return <section className="related-topics"><h3>Связанные объяснения</h3><div className="topic-links">{related.map(topic=><Link key={topic.id} to={'/textbook/'+topic.id}><BookOpen size={15}/>{topic.title}<ArrowUpRightIcon/></Link>)}</div></section>;
}
function ArrowUpRightIcon(){return <ArrowRight size={14}/>}

export function LessonPage(){
  const {lessonId}=useParams();const {catalog}=useStore();
  const control=lessonId?.match(/^M0([1-4])-C\d+-\d+$/);if(control)return <Navigate to={'/assessments?module='+control[1]} replace/>;
  if(!lessonId||!catalog.lessons.some(l=>l.id===lessonId&&l.kind!=='control'))return <Navigate to="/catalog" replace/>;
  return <LoadedLessonPage key={lessonId} lessonId={lessonId}/>;
}

function LoadedLessonPage({lessonId}:{lessonId:string}){
  const {lesson,error}=useLesson(lessonId);const {catalog,local,toggle}=useStore();const [params,setParams]=useSearchParams();
  const requested=params.get('tab')||'lecture';
  useEffect(()=>{if(['practice','original'].includes(requested))setParams({tab:requested==='practice'?'tasks':'lecture'},{replace:true})},[requested]);
  if(error)return <NotFound message={error}/>;if(!lesson)return <Loading/>;
  const l=lesson;const tab=requested==='practice'?'tasks':requested==='original'?'lecture':requested;
  const module=catalog.modules.find(m=>m.id===l.moduleId)!;
  const visible=catalog.lessons.filter(item=>item.kind!=='control');const position=visible.findIndex(item=>item.id===l.id);const prev=visible[position-1],next=visible[position+1];
  const extended=buildExtendedLecture(l);
  const tabs=[{id:'lecture',label:'Оригинальная лекция',icon:FileText},{id:'slides',label:'Презентация',icon:Presentation},{id:'extended',label:'Подробная лекция',icon:BookOpen},...(l.tasks.length?[{id:'tasks',label:`Практические задания · ${l.tasks.length}`,icon:Code2}]:[]),...(l.files.length?[{id:'files',label:'Файлы занятия',icon:FolderOpen}]:[])];
  const active=tabs.some(item=>item.id===tab)?tab:'lecture';
  const headings=active==='extended'?(extended.match(/^#{2,3} .+$/gm)||[]):[];
  return <div className="page lesson-page"><div className="breadcrumbs"><Link to="/catalog">Каталог</Link><ChevronRight size={14}/><Link to={'/module/'+l.moduleId}>Модуль {l.moduleId}</Link><ChevronRight size={14}/><span>{l.number}</span></div>
    <header className="lesson-header"><div><span className="eyebrow">{l.kind==='final'?'ИТОГОВАЯ ЗАЩИТА':l.kind==='assessment'?'ДОКУМЕНТЫ АТТЕСТАЦИИ':'ЗАНЯТИЕ '+l.number}</span><h1>{l.title}</h1><p>{l.description||module.title}</p></div><button className={'icon-button favorite '+(local.favorites.includes(l.id)?'saved':'')} onClick={()=>toggle('favorites',l.id)} aria-label={local.favorites.includes(l.id)?'Убрать из избранного':'Добавить в избранное'}><Bookmark size={21}/></button></header>
    <nav className="lesson-tabs" aria-label="Материалы занятия">{tabs.map(({id,label,icon:Icon})=><button key={id} className={active===id?'active':''} onClick={()=>setParams({tab:id})}><Icon size={18}/>{label}</button>)}</nav>
    {['assessment','final'].includes(l.kind)&&<p><Link className="button" to={'/assessments/'+l.id}>Готовые ответы и объяснения аттестации<ArrowRight size={17}/></Link></p>}
    <div className={'reading-layout '+(['lecture','slides','files'].includes(active)?'document-layout':'')}><div className="reading-main">
      {active==='lecture'&&(l.documents?.lecture?<DocumentReader document={l.documents.lecture}/>:<><div className="content-origin">ИСХОДНАЯ ЛЕКЦИЯ / ТЕКСТ ИЗ АРХИВА</div><Markdown content={l.lecture}/></>)}
      {active==='slides'&&<section>{l.documents?.presentation?<><div className="section-heading"><div><span className="eyebrow">ИСХОДНЫЙ ФАЙЛ iSMART</span><h2>Оригинальная презентация</h2></div>{l.deckDownload&&<a className="button secondary" href={assetUrl(l.deckDownload)} download aria-label="Скачать оригинальную презентацию PPTX">Скачать PPTX</a>}</div><DocumentReader document={l.documents.presentation}/><p className="muted small">Слайды из оригинальной презентации курса, преобразованные в PDF средствами Microsoft PowerPoint. Из скачиваемой студенческой PPTX исключены заметки и служебные метаданные.</p></>:<div className="presentation-missing"><Notice>{l.presentation?.reason||'Оригинальная презентация iSMART отсутствует в архиве.'}</Notice><button className="button secondary" onClick={()=>setParams({tab:'lecture'})}>Читать исходную лекцию<BookOpen size={17}/></button></div>}</section>}
      {active==='extended'&&<article className="extended-lecture"><div className="content-origin">ПОДРОБНОЕ ОБЪЯСНЕНИЕ / CODE FUTURE ACADEMY</div>{extended?<Markdown content={extended}/>:<Markdown content={l.lecture}/>}<RelatedTopics lessonId={l.id} ids={l.extendedTopics}/></article>}
      {active==='tasks'&&<section><div className="section-heading"><h2>Практические задания</h2><span className="muted">Оригинальные элементы iSMART</span></div><TaskList lesson={l}/></section>}
      {active==='files'&&<section><div className="section-heading"><h2>Файлы занятия</h2></div><Files files={l.files}/></section>}
      <nav className="lesson-navigation" aria-label="Соседние занятия">{prev?<Link to={'/lesson/'+prev.id}><ArrowLeft size={18}/><span><small>Предыдущее занятие</small><strong>{prev.number} / {prev.title}</strong></span></Link>:<Link to={'/module/'+l.moduleId}><ArrowLeft size={18}/>К модулю</Link>}{next?<Link to={'/lesson/'+next.id}><span><small>Следующее занятие</small><strong>{next.number} / {next.title}</strong></span><ArrowRight size={18}/></Link>:<Link to="/catalog">Каталог занятий<ArrowRight size={18}/></Link>}</nav>
      <details className="source-details"><summary>Происхождение материалов</summary><p>Комплект iSMART / {l.source.path}. Оригинальные исходники сохранены отдельно. Веб-превью и PDF-конверсии обозначены в описании соответствующего документа.</p></details>
    </div>{!['lecture','slides','files'].includes(active)&&<aside className="lesson-toc"><div className="sticky-toc"><span className="eyebrow">НА ЭТОЙ СТРАНИЦЕ</span><nav>{headings.length?headings.map((heading,index)=><button key={index} onClick={()=>document.getElementById(slug(heading.replace(/^#+ /,'')))?.scrollIntoView({behavior:'smooth'})}>{heading.replace(/^#+ /,'')}</button>):l.tasks.map(task=><Link key={task.id} to={`/lesson/${l.id}/task/${task.id}`}>{task.number}. {task.title}</Link>)}</nav><Link className="text-link" to={'/module/'+l.moduleId}>Все занятия модуля<ArrowRight size={15}/></Link></div></aside>}</div>
  </div>;
}

export function TaskPage(){
  const {lessonId,taskId}=useParams();const {catalog}=useStore();const summary=catalog.lessons.find(l=>l.id===lessonId&&l.kind==='lesson');
  if(!summary)return <Navigate to={lessonId&&catalog.lessons.some(l=>l.id===lessonId)?'/lesson/'+lessonId:'/catalog'} replace/>;
  if(!summary.tasks.some(task=>task.id===taskId&&task.origin==='ismart'))return <Navigate to={'/lesson/'+summary.id+(summary.taskCount?'?tab=tasks':'')} replace/>;
  return <LoadedTaskPage key={taskId} lessonId={summary.id} taskId={taskId!}/>;
}

function LoadedTaskPage({lessonId,taskId}:{lessonId:string;taskId:string}){
  const {lesson,error}=useLesson(lessonId);if(error)return <NotFound message={error}/>;if(!lesson)return <Loading/>;
  const task=lesson.tasks.find(item=>item.id===taskId);if(!task)return <Navigate to={'/lesson/'+lesson.id+'?tab=tasks'} replace/>;
  return <TaskDetail lesson={lesson} task={task}/>;
}

function statementLead(statement:string){
  const beforeCode=statement.split('```')[0].replace(/^#{1,6} .+\n/gm,'').trim();
  const blocks=beforeCode.split(/\n\n/).filter(block=>block.length>25&&!/^Условие|Исходный код$/i.test(block));
  return blocks.slice(0,2).join('\n\n').slice(0,700);
}

function TaskDetail({lesson:l,task:t}:{lesson:Lesson;task:Task}){
  const {local,toggle}=useStore();const index=l.tasks.findIndex(task=>task.id===t.id);const next=l.tasks[index+1],prev=l.tasks[index-1];const solution=t.solution?.status==='published'?t.solution:null;
  const lead=statementLead(t.statement);const isCode=Boolean(solution?.code);
  return <div className="page task-page"><div className="breadcrumbs"><Link to={'/practice?module='+l.moduleId+'&lesson='+l.id}>Занятие {l.number}</Link><ChevronRight size={14}/><span>Задание {t.number}</span></div>
    <header className="lesson-header"><div><span className="eyebrow">ЗАДАНИЕ {t.number} / {taskLabels[t.type]}</span><h1>{t.title}</h1><Link className="lesson-context-link" to={'/lesson/'+l.id}>{l.title}</Link></div><button className={'icon-button favorite '+(local.favorites.includes(t.id)?'saved':'')} onClick={()=>toggle('favorites',t.id)} aria-label={local.favorites.includes(t.id)?'Убрать задание из избранного':'Добавить задание в избранное'}><Bookmark size={21}/></button></header>
    <div className="reading-layout"><div className="reading-main"><section className="task-statement"><h2>Условие</h2>{lead&&<Markdown content={lead}/>}<details className="statement-details"><summary>Полное исходное условие<ChevronDown size={17}/></summary><Markdown content={t.statement}/></details></section>
      <section className="solution-section" id="solution"><div className="section-heading"><h2>{solution?.kind==='project_example'?'Образец выполнения':'Готовое решение'}</h2>{solution&&<span className="solution-status">{solution.verification==='ismart'?'Подтверждено на iSMART':solution.testCount?`Проверено локально · тестов: ${solution.testCount}`:'Проверено по условию'}</span>}</div>
        {solution?<>{isCode&&solution.answer&&<TextAnswer answer={solution.answer} label="Готовый ответ"/>}{isCode?<CodeBlock code={solution.code} label="Python / готовый код"/>:<TextAnswer answer={solution.answer||solution.code} label={solution.kind==='project_example'?'Пример для выбранного кейса':'Готовый ответ'}/>}{solution.artifact&&<a className="button secondary" href={assetUrl(solution.artifact.url)} download>{solution.artifact.label}</a>}<div className="answer-platform"><OfficialLink link={t.ismartLink} lessonTitle={l.title}/></div></>:<div className="answer-missing"><p>Ответ пока не подтверждён. Исходное условие и материалы занятия доступны.</p><OfficialLink link={t.ismartLink} lessonTitle={l.title}/></div>}
      </section>
      {solution&&<details className="solution-explanation"><summary><span><BookOpen size={21}/>Подробное объяснение</span><ChevronDown size={20}/></summary><div><Markdown content={solution.explanation}/>{solution.lineExplanations?.length? <section className="line-explanations"><h3>Что делает каждая строка</h3><dl>{solution.lineExplanations.map((line,i)=><div key={i}><dt>{String(line.line).padStart(2,'0')}</dt><dd>{line.text}</dd></div>)}</dl></section>:null}{solution.examples?.length?<section><h3>Примеры проверки</h3>{solution.examples.slice(0,3).map((example,i)=><div className="solution-example" key={i}>{example.input&&<div><h4>Входные данные</h4><CodeBlock code={example.input} language="text" label="Ввод"/></div>}<div><h4>Результат</h4><CodeBlock code={example.output} language="text" label="Вывод программы"/></div></div>)}</section>:null}<p className="verification-note">Локальная проверка не является проверкой на iSMART. Официальное оценивание выполняется на платформе курса.</p></div></details>}
      {t.type==='file'&&l.files.length>0&&<details className="task-files"><summary><FolderOpen size={20}/>Файлы для этого задания<ChevronDown size={18}/></summary><Files files={l.files.filter(file=>t.files.includes(file.id))}/></details>}
      <RelatedTopics lessonId={l.id} ids={solution?.relatedTopics}/><Link className="extended-link" to={'/lesson/'+l.id+'?tab=extended'}><BookOpen size={21}/><span><strong>Нужно больше контекста?</strong><small>Подробная лекция к занятию {l.number}</small></span><ArrowRight size={20}/></Link>
      <nav className="lesson-navigation" aria-label="Соседние задания">{prev?<Link to={`/lesson/${l.id}/task/${prev.id}`}><ArrowLeft size={18}/><span><small>Предыдущее задание</small><strong>{prev.title}</strong></span></Link>:<Link to={'/lesson/'+l.id+'?tab=tasks'}><ArrowLeft size={18}/>Все задания занятия</Link>}{next?<Link to={`/lesson/${l.id}/task/${next.id}`}><span><small>Следующее задание</small><strong>{next.title}</strong></span><ArrowRight size={18}/></Link>:<Link to={'/lesson/'+l.id}>К материалам занятия<ArrowRight size={18}/></Link>}</nav>
    </div><aside className="lesson-toc"><div className="sticky-toc"><span className="eyebrow">ЗАДАНИЯ / {l.number}</span><nav>{l.tasks.map(task=><Link key={task.id} className={task.id===t.id?'active':''} to={`/lesson/${l.id}/task/${task.id}`}><span>{task.number}.</span>{task.title}</Link>)}</nav><Link className="text-link" to={'/lesson/'+l.id+'?tab=extended'}>Подробная лекция<ArrowRight size={15}/></Link><Link className="text-link" to="/errors">Справочник ошибок<ArrowRight size={15}/></Link></div></aside></div>
  </div>;
}
