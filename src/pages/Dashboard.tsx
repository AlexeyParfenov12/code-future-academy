import {Link} from 'react-router-dom';
import {ArrowRight,ArrowUpRight,BookOpen,Bookmark,BrainCircuit,Code2,FileText,FolderKanban,GraduationCap,Sigma,TriangleAlert} from 'lucide-react';
import type {Module,LessonSummary} from '../models';
import {useStore} from '../state';
import {SearchBox} from '../components/Shell';

export const moduleIcons=[Code2,Sigma,BrainCircuit,FolderKanban,GraduationCap];
export const moduleTags=[['Python','Данные','Алгоритмы'],['Функции','Вероятность','Статистика'],['Scikit-learn','Машинное обучение'],['Требования','Прототип','Документация'],['Итоговая защита']];

export function ModuleCard({module:m}:{module:Module}) {
  const {catalog}=useStore();const lessons=catalog.lessons.filter(l=>l.moduleId===m.id&&l.kind!=='control');
  const published=lessons.flatMap(l=>l.tasks).filter(t=>t.solutionStatus==='published').length;
  return <Link to={'/module/'+m.id} className={'module-entry module-'+m.id}><span className="module-index">0{m.id}<span>/</span></span><div className="module-entry-copy"><span className="eyebrow">{m.id===5?'СПРАВОЧНЫЕ МАТЕРИАЛЫ':'МОДУЛЬ '+m.id}</span><h3>{m.title}</h3><p>{m.description}</p><div className="module-meta"><span>{lessons.length} занятий</span><span>{published>0?`${published} готовых ответов`:moduleTags[m.id-1].join(' / ')}</span></div></div><ArrowUpRight size={23}/></Link>;
}

export function LessonRow({lesson:l}:{lesson:LessonSummary}) {
  const {local,toggle}=useStore();const published=l.tasks.filter(t=>t.solutionStatus==='published').length;
  return <div className="lesson-row"><span className="lesson-number">{l.number}</span><Link to={'/lesson/'+l.id} className="lesson-row-main"><strong>{l.title}</strong><span>{l.kind==='assessment'?'Документы промежуточной аттестации':l.kind==='final'?'Требования, критерии и защита проекта':`${l.slideCount} слайдов${l.taskCount?` · ${l.taskCount} официальных заданий`:''}${published?` · ${published} ответов`:''}`}</span></Link><button className={'icon-button favorite '+(local.favorites.includes(l.id)?'saved':'')} onClick={()=>toggle('favorites',l.id)} aria-label={local.favorites.includes(l.id)?'Убрать из избранного':'Добавить в избранное'}><Bookmark size={18}/></button><Link className="row-arrow" to={'/lesson/'+l.id} aria-label={'Открыть '+l.number}><ArrowRight size={18}/></Link></div>;
}

export function Dashboard() {
  const {catalog,local}=useStore();
  const recent=local.recent.map(id=>catalog.lessons.find(l=>l.id===id)).filter((l):l is LessonSummary=>Boolean(l)).slice(0,4);
  const published=catalog.lessons.flatMap(l=>l.tasks).filter(t=>t.solutionStatus==='published').length;
  return <div className="page reference-home"><header className="home-intro"><div className="eyebrow">PYTHON / ДАННЫЕ / ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ</div><h1>Code Future Academy<span className="title-dot">.</span></h1><p>Лекции, презентации, готовые решения и подробные объяснения<br className="desktop-break"/> курса «Разработчик интеллектуальных решений».</p><SearchBox large/></header>
    <section className="intent-links" aria-label="Быстрый доступ"><Link to="/practice"><span className="intent-number">01</span><div><h2>Найти готовое решение</h2><p>Официальное задание → ответ → копирование → iSMART</p></div><ArrowRight size={25}/></Link><Link to="/textbook"><span className="intent-number">02</span><div><h2>Разобраться в теме</h2><p>Понятные объяснения, примеры программ и источники</p></div><ArrowRight size={25}/></Link></section>
    <div className="home-body"><section><div className="section-heading"><h2>Индекс курса</h2><span className="muted">{catalog.counts.lectures||74} лекции · {published} опубликованных ответов</span></div><div className="module-index-list">{catalog.modules.map(module=><ModuleCard module={module} key={module.id}/>)}</div></section>
      <aside className="home-reference"><span className="eyebrow">ОТКРЫТЬ НУЖНОЕ</span><Link to="/lesson/M01-L03?tab=tasks"><span>01.03 / Практика</span><strong>Первые программы на Python</strong><ArrowUpRight size={18}/></Link><Link to="/textbook/variables"><span>Учебник Python</span><strong>Переменные и присваивание</strong><ArrowUpRight size={18}/></Link><Link to="/errors"><span>Справочник</span><strong>Что означает ошибка Python</strong><TriangleAlert size={18}/></Link><div className="reference-note"><FileText size={24}/><h3>Ответ и объяснение — рядом</h3><p>Готовый код можно скопировать сразу. Разбор, исходные документы и связанные темы доступны на той же странице.</p><a href={catalog.course.officialUrl} target="_blank" rel="noopener noreferrer">Официальная проверка — на iSMART<ArrowUpRight size={15}/></a></div></aside>
    </div>
    {recent.length>0&&<section className="recent-section"><div className="section-heading"><h2>Недавно открыто</h2><Link className="text-link" to="/favorites">Избранное<Bookmark size={16}/></Link></div><div className="lesson-list">{recent.map(lesson=><LessonRow key={lesson.id} lesson={lesson}/>)}</div></section>}
    <section className="library-directory"><Link to="/textbook"><BookOpen size={22}/><h3>Учебник Python</h3><p>72 главы: от основ до анализа данных</p><ArrowUpRight size={18}/></Link><Link to="/ai"><BrainCircuit size={22}/><h3>Искусственный интеллект</h3><p>73 главы: ML, нейросети, LLM и RAG</p><ArrowUpRight size={18}/></Link><Link to="/resources"><FileText size={22}/><h3>Источники и инструменты</h3><p>94 источника, курса и инструмента</p><ArrowUpRight size={18}/></Link></section>
  </div>;
}
