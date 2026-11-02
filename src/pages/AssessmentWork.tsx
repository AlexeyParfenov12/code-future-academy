import {useEffect,useState} from 'react';
import {Link,useParams,useSearchParams} from 'react-router-dom';
import {ArrowLeft,ArrowRight,BookOpen,ChevronRight,Download} from 'lucide-react';
import {getJSON,assetUrl} from '../data';
import {CodeBlock,Markdown,Notice,OfficialLink,TextAnswer} from '../components/Content';
import type {IsmartLink,TaskSolution} from '../models';
import {Loading,NotFound} from './Lessons';

type ReviewSolution=Omit<TaskSolution,'status'>&{status:'published'|'unavailable';reason?:string};
type Variant={id:string;title:string;statement:string;solution:ReviewSolution;sourceIssues:string[];ismartLink:IsmartLink|null};
type ReviewTask={id:string;number:number;title:string;variants:Variant[]};
type Work={id:string;moduleId:number;title:string;kind:'control'|'assessment'|'final';number:string;documentUrl?:string;tasks:ReviewTask[]};
function useWork(id?:string){
 const [work,setWork]=useState<Work|null>(null);const [failed,setFailed]=useState(false);
 useEffect(()=>{setWork(null);setFailed(false);const controller=new AbortController();getJSON<Work>('/content/assessments/'+encodeURIComponent(id||'')+'.json',controller.signal).then(setWork).catch(()=>{if(!controller.signal.aborted)setFailed(true)});return()=>controller.abort()},[id]);
 return {work,failed};
}
const label=(work:Work)=>work.kind==='control'?'ТЕКУЩИЙ КОНТРОЛЬ':work.kind==='final'?'ИТОГОВАЯ ЗАЩИТА':'ПРОМЕЖУТОЧНАЯ АТТЕСТАЦИЯ';
export function AssessmentWorkPage(){
 const {assessmentId}=useParams();const {work,failed}=useWork(assessmentId);
 if(failed)return <NotFound/>;if(!work)return <Loading/>;
 return <div className="page"><div className="breadcrumbs"><Link to="/assessments">Контроли и аттестации</Link><ChevronRight size={14}/><Link to={'/assessments?module='+work.moduleId}>Модуль {work.moduleId}</Link></div><header className="page-heading"><div><span className="eyebrow">{label(work)}</span><h1>{work.title}</h1><p>Выберите вопрос или задание: ответ доступен сразу, подробный разбор — рядом.</p></div>{work.documentUrl&&<Link className="button secondary" to={work.documentUrl}><BookOpen size={17}/>Исходные документы</Link>}</header>
 <div className="task-list">{work.tasks.map(task=><Link className="task-card assessment-task-card" key={task.id} to={'/assessments/'+work.id+'/task/'+task.id}><span className="task-list-number">{task.number}</span><div className="task-card-main"><strong>{task.title}</strong><p>{task.variants[0].statement.split('\n').find(line=>line.trim())?.replace(/^#+ /,'').slice(0,180)}</p><span>{task.variants.some(v=>v.solution.status==='published')?'Готовый ответ и объяснение':'Нет полного условия в архиве'}{task.variants.length>1?' · Вариантов: '+task.variants.length:''}</span></div><ArrowRight size={19}/></Link>)}</div>
 </div>;
}
export function AssessmentAnswerPage(){
 const {assessmentId,taskId}=useParams();const {work,failed}=useWork(assessmentId);const [params,setParams]=useSearchParams();
 if(failed)return <NotFound/>;if(!work)return <Loading/>;
 const index=work.tasks.findIndex(t=>t.id===taskId);const task=work.tasks[index];if(!task)return <NotFound/>;
 const variantIndex=Math.max(0,Math.min(task.variants.length-1,Number(params.get('variant')||1)-1))||0;
 const variant=task.variants[variantIndex];const solution=variant.solution;const published=solution.status==='published';
 const previous=work.tasks[index-1],next=work.tasks[index+1];
 function downloadAnswer(){const url=URL.createObjectURL(new Blob([solution.kind==='code'?solution.code:(solution.answer||solution.code)],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=work!.id+'-'+task.number+(solution.kind==='code'?'-solution.py':'-answer.txt');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 return <div className="page task-page assessment-answer-page"><div className="breadcrumbs"><Link to="/assessments">Контроли и аттестации</Link><ChevronRight size={14}/><Link to={'/assessments/'+work.id}>{work.title}</Link></div><header className="lesson-header"><div><span className="eyebrow">{label(work)} / МОДУЛЬ {work.moduleId}</span><h1>{task.title}</h1></div></header>
 {task.variants.length>1?<label className="assessment-variant-label">Вариант задания<select aria-label="Вариант задания" value={variantIndex} onChange={e=>setParams({variant:String(Number(e.target.value)+1)})}>{task.variants.map((v,i)=><option value={i} key={v.id}>{v.title}</option>)}</select></label>:<p className="muted small">{variant.title}</p>}
 <div className="reading-layout"><div className="reading-main"><section className="task-statement"><h2>Условие</h2><Markdown content={variant.statement}/>{variant.sourceIssues.map(issue=><Notice key={issue}>{issue}</Notice>)}</section>
 <section className="solution-section"><div className="section-heading"><h2>{solution.kind==='project_example'?'Готовый образец проекта':'Готовый ответ'}</h2>{published&&<span className="solution-status">{solution.testCount?'Проверено локально · тестов: '+solution.testCount:'Проверено по условию'}</span>}</div>
 {published?<>{solution.code&&solution.kind==='code'&&<CodeBlock code={solution.code} label="Python / готовое решение"/>}{solution.answer&&<TextAnswer answer={solution.answer} label={solution.kind==='code'?'Проверенный вывод':'Готовый ответ'}/>} <div className="assessment-answer-actions"><button className="button secondary" onClick={downloadAnswer}><Download size={17}/>{solution.kind==='code'?'Скачать код PY':'Скачать ответ TXT'}</button>{solution.artifact&&<a className="button" href={assetUrl(solution.artifact.url)} download>{solution.artifact.label}<Download size={17}/></a>}</div>{solution.code&&solution.kind!=='code'&&(solution.kind==='project_example'?<details className="source-details"><summary>Код готового проекта</summary><CodeBlock code={solution.code}/></details>:<CodeBlock code={solution.code} label="Python / готовое решение"/>)}</>:<Notice>{solution.reason}</Notice>}
 </section>
 {published&&<details className="solution-explanation"><summary><span><BookOpen size={20}/>Подробное объяснение</span></summary><div><Markdown content={solution.explanation}/>{solution.lineExplanations?.length?<section className="line-explanations"><h3>Разбор строк</h3><dl>{solution.lineExplanations.map(line=><div key={line.line}><dt>{line.line}</dt><dd>{line.text}</dd></div>)}</dl></section>:null}{solution.examples?.map((example,i)=><div key={i}><h3>Проверка программы {i+1}</h3>{example.input&&<CodeBlock code={example.input} language="text" label="Вход"/>}<CodeBlock code={example.output} language="text" label="Проверенный вывод"/></div>)}</div></details>}
 <OfficialLink link={variant.ismartLink} lessonTitle={work.title}/>
 <nav className="lesson-navigation">{previous?<Link to={'/assessments/'+work.id+'/task/'+previous.id}><ArrowLeft size={17}/>{previous.title}</Link>:<Link to={'/assessments/'+work.id}><ArrowLeft size={17}/>Все задания</Link>}{next&&<Link to={'/assessments/'+work.id+'/task/'+next.id}>{next.title}<ArrowRight size={17}/></Link>}</nav>
 </div><aside className="lesson-toc"><div className="sticky-toc"><span className="eyebrow">ВОПРОСЫ И ЗАДАНИЯ</span><nav>{work.tasks.map(t=><Link className={t.id===task.id?'active':''} key={t.id} to={'/assessments/'+work.id+'/task/'+t.id}>{t.title}</Link>)}</nav>{work.documentUrl&&<Link className="text-link" to={work.documentUrl}>Исходные документы<ArrowRight size={15}/></Link>}</div></aside></div>
 </div>;
}
