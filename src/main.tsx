import {StrictMode,useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {HashRouter,Route,Routes} from 'react-router-dom';
import type {Catalog} from './models';
import {getCatalog} from './data';
import {Provider} from './state';
import {Shell} from './components/Shell';
import {Dashboard} from './pages/Dashboard';
import {CatalogPage,ModulePage,PracticePage} from './pages/Catalog';
import {LessonPage,Loading,NotFound,TaskPage} from './pages/Lessons';
import {TextbookPage,TopicPage,ErrorsPage,ResourcesPage,LabPage} from './pages/Library';
import {FavoritesPage,ProgressPage,ImportReportPage} from './pages/Personal';
import './styles.css';
function App(){const [catalog,setCatalog]=useState<Catalog|null>(null);const [error,setError]=useState(false);useEffect(()=>{getCatalog().then(setCatalog).catch(()=>setError(true))},[]);if(error)return <div className="standalone-error"><h1>Материалы не загрузились</h1><p>Проверьте подключение и повторите загрузку.</p><button className="button" onClick={()=>window.location.reload()}>Обновить страницу</button></div>;if(!catalog)return <Loading/>;return <Provider catalog={catalog}><HashRouter><Routes><Route element={<Shell/>}><Route index element={<Dashboard/>}/><Route path="catalog" element={<CatalogPage/>}/><Route path="module/:moduleId" element={<ModulePage/>}/><Route path="lesson/:lessonId" element={<LessonPage/>}/><Route path="lesson/:lessonId/task/:taskId" element={<TaskPage/>}/><Route path="practice" element={<PracticePage/>}/><Route path="textbook" element={<TextbookPage/>}/><Route path="textbook/:topicId" element={<TopicPage/>}/><Route path="ai" element={<TextbookPage ai/>}/><Route path="errors" element={<ErrorsPage/>}/><Route path="resources" element={<ResourcesPage/>}/><Route path="lab" element={<LabPage/>}/><Route path="favorites" element={<FavoritesPage/>}/><Route path="progress" element={<ProgressPage/>}/><Route path="import-report" element={<ImportReportPage/>}/><Route path="*" element={<NotFound/>}/></Route></Routes></HashRouter></Provider>}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
