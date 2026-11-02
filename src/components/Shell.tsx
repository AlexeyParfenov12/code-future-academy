import {useEffect,useMemo,useRef,useState} from 'react';
import {Link,NavLink,Outlet,useLocation,useNavigate} from 'react-router-dom';
import {ArrowRight,ArrowUpRight,BookOpen,Bookmark,BrainCircuit,Check,ChevronDown,ChevronRight,Code2,ClipboardCheck,Command,FileText,House,Library,Menu,Moon,Search,Sun,TriangleAlert,X} from 'lucide-react';
import Fuse from 'fuse.js';
import {topics} from '../learning';
import {useStore} from '../state';
import {getJSON} from '../data';

type SearchRecord={id:string;title:string;context:string;url:string;body?:string;aliases?:string};
const navigation=[{to:'/',label:'Обзор библиотеки',icon:House},{to:'/catalog',label:'Все занятия',icon:BookOpen},{to:'/practice',label:'Готовые решения',icon:Code2},{to:'/assessments',label:'Контроли и аттестации',icon:ClipboardCheck}];
const reference=[{to:'/textbook',label:'Учебник Python',icon:BookOpen},{to:'/ai',label:'Искусственный интеллект',icon:BrainCircuit},{to:'/errors',label:'Справочник ошибок',icon:TriangleAlert},{to:'/resources',label:'Источники и инструменты',icon:Library}];

export function SearchBox({large=false}:{large?:boolean}) {
  const {catalog}=useStore();const [query,setQuery]=useState('');const [open,setOpen]=useState(false);const [full,setFull]=useState<SearchRecord[]>([]);
  const input=useRef<HTMLInputElement>(null);const box=useRef<HTMLDivElement>(null);const navigate=useNavigate();
  useEffect(()=>{
    const key=(event:KeyboardEvent)=>{if((event.ctrlKey||event.metaKey)&&event.key==='k'){event.preventDefault();input.current?.focus();setOpen(true)}if(event.key==='Escape')setOpen(false)};
    const outside=(event:MouseEvent)=>{if(!box.current?.contains(event.target as Node))setOpen(false)};
    document.addEventListener('keydown',key);document.addEventListener('mousedown',outside);
    return()=>{document.removeEventListener('keydown',key);document.removeEventListener('mousedown',outside)};
  },[]);
  useEffect(()=>{if(open&&!full.length)getJSON<SearchRecord[]>('/content/search-index.json').then(setFull).catch(()=>{})},[open,full.length]);
  const records=useMemo<SearchRecord[]>(()=>[...(full.length?full:catalog.lessons.filter(l=>l.kind!=='control').flatMap(l=>[
    {id:l.id,title:l.title,context:'Занятие '+l.number,url:'/lesson/'+l.id},
    ...l.tasks.filter(t=>t.origin==='ismart').map(t=>({id:t.id,title:t.title,context:`Задание ${t.number} · Занятие ${l.number}`,url:`/lesson/${l.id}/task/${t.id}`}))
  ])),...topics.map(t=>({id:'topic-'+t.id,title:t.title,context:'Учебник / '+t.group,url:'/textbook/'+t.id,body:t.content}))],[catalog,full]);
  const results=useMemo(()=>{const numbered=query.match(/^(\d+\.\d+)\s*(?:№|задание)\s*(\d+)$/i);if(numbered)return records.filter(r=>r.aliases?.startsWith(numbered[1]+' №'+numbered[2]+' ')).slice(0,8);return query.trim()?new Fuse(records,{keys:[{name:'title',weight:.45},{name:'aliases',weight:.25},{name:'context',weight:.2},{name:'body',weight:.1}],threshold:.3,ignoreLocation:true}).search(query.trim()).slice(0,8).map(r=>r.item):[]},[query,records]);
  return <div className={'search-box '+(large?'search-large':'')} ref={box}>
    <Search size={large?23:19}/><input ref={input} value={query} placeholder={large?'Найти занятие, задание, функцию или тему…':'Поиск по библиотеке…'} aria-label="Глобальный поиск" onFocus={()=>setOpen(true)} onChange={event=>{setQuery(event.target.value);setOpen(true)}} onKeyDown={event=>{if(event.key==='Enter'&&results[0]){navigate(results[0].url);setOpen(false)}}}/><kbd><Command size={13}/> K</kbd>
    {open&&query&&<div className="search-results"><div className="search-caption">МАТЕРИАЛЫ ПО ЗАПРОСУ</div>{results.length?results.map(result=><Link key={result.id} to={result.url} onClick={()=>setOpen(false)}><span><small>{result.context}</small><strong>{result.title}</strong></span><ArrowRight size={17}/></Link>):<p>Ничего не найдено. Попробуйте номер занятия, название задания или функцию Python.</p>}</div>}
  </div>;
}

export function Shell() {
  const {catalog,local,theme,storageAvailable,notice}=useStore();const [mobile,setMobile]=useState(false);const location=useLocation();
  const home=location.pathname==='/';
  useEffect(()=>{setMobile(false);window.scrollTo(0,0)},[location.pathname]);
  const current=catalog.lessons.find(l=>location.pathname.includes(l.id));
  const page=[...navigation,...reference].find(item=>item.to!=='/'&&location.pathname.startsWith(item.to))?.label||(current?'Занятие '+current.number:'Библиотека');
  return <div className="app-shell">
    <a className="skip-link" href="#main" onClick={event=>{event.preventDefault();document.getElementById('main')?.focus()}}>К содержимому</a>
    {mobile&&<button className="mobile-scrim" onClick={()=>setMobile(false)} aria-label="Закрыть меню"/>}
    <aside className={'sidebar '+(mobile?'mobile-open':'')}>
      <Link to="/" className="brand"><span className="brand-mark"><Code2 size={25}/></span><span>code future<small>ACADEMY / БИБЛИОТЕКА</small></span></Link>
      <button className="mobile-close icon-button" aria-label="Закрыть меню" onClick={()=>setMobile(false)}><X size={21}/></button>
      <div className="sidebar-scroll">
        <div className="nav-label">МАТЕРИАЛЫ КУРСА</div><nav aria-label="Основная навигация">{navigation.map(({to,label,icon:Icon})=><NavLink key={to} to={to} end={to==='/'}><Icon size={18}/>{label}</NavLink>)}</nav>
        <div className="course-index"><div className="nav-label">ИНДЕКС МОДУЛЕЙ</div>{catalog.modules.map(module=><details key={module.id} open={current?.moduleId===module.id||undefined}><summary><span className="index-number">0{module.id}</span><span>{module.id===1?'Python и данные':module.id===2?'Математика для ИИ':module.id===3?'Модели и алгоритмы':module.id===4?'Проектирование':'Итоговая защита'}</span><ChevronDown size={14}/></summary><div className="course-index-lessons"><Link className="module-index-link" to={'/module/'+module.id}>Все материалы модуля<ArrowUpRight size={13}/></Link>{catalog.lessons.filter(l=>l.moduleId===module.id&&l.kind!=='control').map(lesson=><NavLink key={lesson.id} to={'/lesson/'+lesson.id}><span>{lesson.number}</span>{lesson.title}</NavLink>)}</div></details>)}</div>
        <div className="nav-label">РАЗОБРАТЬСЯ В ТЕМЕ</div><nav>{reference.map(({to,label,icon:Icon})=><NavLink key={to} to={to}><Icon size={18}/>{label}</NavLink>)}<NavLink to="/favorites"><Bookmark size={18}/>Избранное{local.favorites.length>0&&<span className="count-badge">{local.favorites.length}</span>}</NavLink></nav>
      </div>
      <a className="platform-link" href={catalog.course.officialUrl} target="_blank" rel="noopener noreferrer"><span><strong>Официальная платформа</strong><small>Сдача и проверка — iSMART</small></span><ArrowUpRight size={19}/></a>
    </aside>
    <div className="workspace"><header className="topbar"><button className="mobile-menu icon-button" onClick={()=>setMobile(true)} aria-label="Открыть меню"><Menu size={22}/></button><div className="top-breadcrumb"><Link to="/">Библиотека</Link>{!home&&<><ChevronRight size={14}/><span>{page}</span></>}</div>{!home&&<SearchBox/>}<button className="icon-button theme-toggle" onClick={theme} aria-label={local.theme==='light'?'Включить тёмную тему':'Включить светлую тему'}>{local.theme==='light'?<Moon size={20}/>:<Sun size={20}/>}</button></header>
      <main id="main" tabIndex={-1}>{!storageAvailable&&<div className="storage-warning">Браузер не сохраняет закладки и настройки.</div>}<Outlet/></main>
      <footer className="site-footer"><span><strong>Code Future Academy</strong> / 2026</span><span>Справочник курса «Разработчик интеллектуальных решений»</span><Link to="/import-report"><FileText size={14}/>Состав и источники</Link></footer>
    </div>
    {notice&&<div role="status" className="toast"><Check size={18}/>{notice}</div>}
  </div>;
}
