import {useEffect,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {ArrowRight,ArrowUpRight,BookOpen,ClipboardCheck,FileText,GraduationCap} from 'lucide-react';
import {getJSON} from '../data';
import {useStore} from '../state';
import {Notice} from '../components/Content';
import {Loading} from './Lessons';

type AssessmentEntry={id:string;moduleId:number;order:number;number:string;title:string;kind:'control'|'assessment'|'final';url?:string;taskCount?:number;solutionCount?:number;candidateUrl?:string|null;linkStatus?:'unverified';documentUrl?:string};
type AssessmentIndex={answerCoverage?:{published:number;missing:number};entries:AssessmentEntry[];counts:{control:number;assessment:number;final:number}};

export function AssessmentsPage(){
 const {catalog}=useStore();const [params]=useSearchParams();const [data,setData]=useState<AssessmentIndex|null>(null);const [failed,setFailed]=useState(false);
 const selected=Number(params.get('module'));const module=catalog.modules.find(m=>m.id===selected);
 useEffect(()=>{const controller=new AbortController();getJSON<AssessmentIndex>('/content/assessments.json',controller.signal).then(setData).catch(()=>{if(!controller.signal.aborted)setFailed(true)});return()=>controller.abort()},[]);
 if(failed)return <div className="page"><h1>Контроли и аттестации</h1><Notice>Список не загрузился. Обновите страницу.</Notice></div>;
 if(!data)return <Loading/>;
 const modules=catalog.modules.filter(m=>!module||m.id===module.id);
 return <div className="page assessments-page"><header className="page-heading"><div><span className="eyebrow">ПРОВЕРОЧНЫЕ РАБОТЫ / ПО МОДУЛЯМ</span><h1>Контроли и аттестации<span className="title-dot">.</span></h1><p>Условия, готовые ответы и объяснения по модулям. Документы и официальные задания — рядом.</p></div></header>
  <p className="muted">Текущих контролей: {data.counts.control} · Промежуточных аттестаций: {data.counts.assessment} · Итоговая защита: {data.counts.final}</p>
  {data.answerCoverage&&<p className="muted small">Готовых разборов с учётом вариантов: {data.answerCoverage.published}. Нет полного условия: {data.answerCoverage.missing}.</p>}
  <nav className="solution-module-tabs" aria-label="Модули контролей и аттестаций"><Link className={!module?'active':''} to="/assessments">Все модули</Link>{catalog.modules.map(m=><Link key={m.id} className={module?.id===m.id?'active':''} to={'/assessments?module='+m.id}>Модуль {m.id}</Link>)}</nav>
  <Notice>Ссылки на контроли восстановлены из архива и ещё не проверены в авторизованном студенческом кабинете. Если ссылка не откроется, найдите контроль на <a href={catalog.course.officialUrl} target="_blank" rel="noopener noreferrer">платформе iSMART</a>. Разборы относятся к сохранённым условиям; проверка на платформе отдельно не выполнялась.</Notice>
  {modules.map(m=><section className="assessment-module" key={m.id}><div className="section-heading"><h2>Модуль {m.id}</h2><span className="muted">{m.title}</span></div><div className="assessment-list">{data.entries.filter(e=>e.moduleId===m.id).sort((a,b)=>a.order-b.order).map(entry=><article className={'assessment-entry assessment-'+entry.kind} key={entry.id}>
   <div className="assessment-symbol">{entry.kind==='control'?<ClipboardCheck size={23}/>:entry.kind==='final'?<GraduationCap size={25}/>:<FileText size={23}/>}</div>
   <div><span className="eyebrow">{entry.kind==='control'?'ТЕКУЩИЙ КОНТРОЛЬ':entry.kind==='assessment'?'ПРОМЕЖУТОЧНАЯ АТТЕСТАЦИЯ / '+entry.number:'ИТОГОВАЯ АТТЕСТАЦИЯ'}</span><h3>{entry.title}</h3>{entry.kind==='control'?<p>Заданий: {entry.taskCount}. Доступны готовые ответы и объяснения.</p>:<p>{entry.kind==='final'?'Требования к проекту, критерии и материалы защиты.':'Исходные учебные документы аттестации.'}</p>}</div>
   <div className="assessment-entry-actions"><Link className="button" to={entry.url||'/assessments/'+entry.id}>Задания и решения<ArrowRight size={17}/></Link>{entry.kind==='control'?<a className="text-link" href={entry.candidateUrl||catalog.course.officialUrl} target="_blank" rel="noopener noreferrer">Открыть контроль на iSMART<ArrowUpRight size={17}/></a>:<Link className="text-link" to={entry.documentUrl!}>Открыть документы<BookOpen size={17}/></Link>}</div>
  </article>)}</div></section>)}
 </div>;
}
