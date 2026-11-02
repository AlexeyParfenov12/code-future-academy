import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {Download} from 'lucide-react';
import {assetUrl,getJSON} from '../data';

type Coverage={total:number;published:number;modules:{module:number;officialTasks:number;codeTasks:number;textTasks:number;publishedSolutions:number;verifiedSolutions:number;withoutSolutions:number;withExplanations:number;verifiedIsmartLinks:number}[];tasks:{taskId:string;lessonId:string;lesson:string;title:string;published:boolean;reason:string|null}[]};
export function CoverageReport(){
 const [coverage,setCoverage]=useState<Coverage|null>(null);
 useEffect(()=>{getJSON<Coverage>('/content/solution-coverage.json').then(setCoverage).catch(()=>setCoverage(null))},[]);
 if(!coverage)return null;
 const missing=coverage.tasks.filter(task=>!task.published);
 return <section className="coverage-report"><div className="section-heading"><div><span className="eyebrow">ОБЫЧНЫЕ ПРАКТИКИ / ПУБЛИЧНЫЙ КАТАЛОГ</span><h2>Готовые ответы: {coverage.published} из {coverage.total}</h2></div><a className="text-link" href={assetUrl('/content/solution-coverage.json')} download><Download size={16}/>Подробный отчёт</a></div>
 <p>В таблице показана полнота материалов справочника. «Локально проверены» — программы, запущенные на примерах и файлах. Текстовые и расчётные ответы отдельно сверены с условиями. Проверка на iSMART выполняется в студенческой сессии.</p>
 <div className="table-scroll"><table><thead><tr><th>Модуль</th><th>Официальных заданий</th><th>Код / прочие</th><th>Ответов</th><th>Локально проверены</th><th>С объяснением</th><th>Без ответа</th><th>Ссылки проверены на iSMART</th></tr></thead><tbody>{coverage.modules.map(module=><tr key={module.module}><td><Link to={'/module/'+module.module}>{String(module.module).padStart(2,'0')}</Link></td><td>{module.officialTasks}</td><td>{module.codeTasks} / {module.textTasks}</td><td>{module.publishedSolutions}</td><td>{module.verifiedSolutions}</td><td>{module.withExplanations}</td><td>{module.withoutSolutions}</td><td>{module.verifiedIsmartLinks}</td></tr>)}</tbody></table></div>
 {missing.length>0&&<details className="missing-solutions"><summary>Задания без опубликованного ответа · {missing.length}</summary><ul>{missing.map(task=><li key={task.taskId}><Link to={`/lesson/${task.lessonId}/task/${task.taskId}`}>{task.lesson} / {task.title}</Link><p>{task.reason}</p></li>)}</ul></details>}
 </section>;
}
