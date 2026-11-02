import {useEffect,useRef,useState} from 'react';
import type {PDFDocumentProxy,RenderTask} from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import {ArrowUpRight,ChevronLeft,ChevronRight,Download,Maximize,Minimize,Minus,Plus} from 'lucide-react';
import type {DocumentAsset} from '../models';
import {assetUrl} from '../data';

export function DocumentReader({document:file}:{document:DocumentAsset}) {
  const [pdf,setPdf]=useState<PDFDocumentProxy|null>(null);
  const [page,setPage]=useState(1);
  const [zoom,setZoom]=useState(1);
  const [width,setWidth]=useState(700);
  const [full,setFull]=useState(false);
  const [error,setError]=useState('');
  const [rendering,setRendering]=useState(false);
  const [pageText,setPageText]=useState('');
  const shell=useRef<HTMLElement>(null);
  const viewport=useRef<HTMLDivElement>(null);
  const canvas=useRef<HTMLCanvasElement>(null);

  useEffect(()=>{
    let live=true;
    let destroy:(()=>void)|undefined;
    setPdf(null);setPage(1);setZoom(1);setError('');
    import('pdfjs-dist').then(lib=>{
      if(!live)return;
      lib.GlobalWorkerOptions.workerSrc=workerUrl;
      const loading=lib.getDocument({url:assetUrl(file.url)});
      destroy=()=>{void loading.destroy()};
      loading.promise.then(doc=>{if(live)setPdf(doc)}).catch(()=>{if(live)setError('Не удалось открыть PDF в просмотрщике. Документ можно открыть отдельно или скачать.')});
    }).catch(()=>{if(live)setError('Просмотрщик не загрузился. Откройте PDF отдельно.')});
    return()=>{live=false;destroy?.()};
  },[file.url]);

  useEffect(()=>{
    if(!viewport.current)return;
    const observer=new ResizeObserver(entries=>setWidth(Math.max(240,entries[0].contentRect.width-40)));
    observer.observe(viewport.current);
    return()=>observer.disconnect();
  },[]);

  useEffect(()=>{
    if(!pdf||!canvas.current)return;
    let live=true;let task:RenderTask|undefined;
    setRendering(true);setError('');
    pdf.getPage(page).then(async pdfPage=>{
      if(!live||!canvas.current)return;
      const original=pdfPage.getViewport({scale:1});
      const view=pdfPage.getViewport({scale:Math.min(width,1000)/original.width*zoom});
      const ratio=Math.min(window.devicePixelRatio||1,2);
      const element=canvas.current;
      element.width=Math.ceil(view.width*ratio);element.height=Math.ceil(view.height*ratio);
      element.style.width=`${view.width}px`;element.style.height=`${view.height}px`;
      const context=element.getContext('2d');if(!context)throw new Error('Canvas unavailable');
      task=pdfPage.render({canvas:element,canvasContext:context,viewport:view,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]});
      await task.promise;
      if(!live)return;
      const text=await pdfPage.getTextContent();
      if(live){setPageText(text.items.map(item=>'str' in item?item.str:'').join(' '));setRendering(false)}
    }).catch(e=>{if(live&&e.name!=='RenderingCancelledException'){setError('Эта страница не отобразилась. Попробуйте открыть исходный PDF отдельно.');setRendering(false)}});
    return()=>{live=false;task?.cancel()};
  },[pdf,page,width,zoom]);

  useEffect(()=>{
    const change=()=>setFull(Boolean(document.fullscreenElement));
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setFull(false)};
    document.addEventListener('fullscreenchange',change);document.addEventListener('keydown',escape);
    return()=>{document.removeEventListener('fullscreenchange',change);document.removeEventListener('keydown',escape)};
  },[]);

  async function fullscreen(){
    try{if(document.fullscreenElement)await document.exitFullscreen();else if(full)setFull(false);else await shell.current?.requestFullscreen()}
    catch{setFull(value=>!value)}
  }

  return <section className={'document-reader '+(full?'reader-fullscreen':'')} ref={shell} aria-label="Просмотр PDF">
    <div className="document-title"><div><span className="eyebrow">ДОКУМЕНТ / PDF</span><h2>{file.label}</h2></div><div className="document-actions">
      <a className="icon-button" href={assetUrl(file.url)} target="_blank" rel="noopener noreferrer" aria-label="Открыть PDF отдельно"><ArrowUpRight size={19}/></a>
      <a className="button secondary" href={assetUrl(file.url)} download={file.name}><Download size={17}/>Скачать PDF</a>
      <button className="icon-button" onClick={fullscreen} aria-label={full?'Выйти из полноэкранного PDF':'PDF на весь экран'}>{full?<Minimize size={19}/>:<Maximize size={19}/>}</button>
    </div></div>
    <div className="pdf-toolbar"><div className="pdf-pagination">
      <button className="icon-button" disabled={!pdf||page===1} onClick={()=>setPage(p=>p-1)} aria-label="Предыдущая страница PDF"><ChevronLeft size={19}/></button>
      <label>Страница <select aria-label="Страница PDF" value={page} onChange={e=>setPage(Number(e.target.value))}>{Array.from({length:pdf?.numPages||1},(_,i)=><option key={i} value={i+1}>{i+1}</option>)}</select><span>из {pdf?.numPages||'…'}</span></label>
      <button className="icon-button" disabled={!pdf||page===pdf.numPages} onClick={()=>setPage(p=>p+1)} aria-label="Следующая страница PDF"><ChevronRight size={19}/></button>
    </div><div className="pdf-zoom"><button className="icon-button" aria-label="Уменьшить PDF" disabled={zoom<=.5} onClick={()=>setZoom(z=>Math.max(.5,z-.25))}><Minus size={17}/></button><button className="text-link" onClick={()=>setZoom(1)} title="Подогнать по ширине">{Math.round(zoom*100)}%</button><button className="icon-button" aria-label="Увеличить PDF" disabled={zoom>=3} onClick={()=>setZoom(z=>Math.min(3,z+.25))}><Plus size={17}/></button></div></div>
    <div className="pdf-viewport" tabIndex={0} onKeyDown={event=>{if(!pdf)return;if(event.key==='ArrowRight'){event.preventDefault();setPage(p=>Math.min(pdf.numPages,p+1))}if(event.key==='ArrowLeft'){event.preventDefault();setPage(p=>Math.max(1,p-1))}}} ref={viewport} aria-busy={rendering||!pdf}>
      {!pdf&&!error&&<div className="document-loading">Открываем документ…</div>}
      {error&&<p className="document-error" role="status">{error} <a href={assetUrl(file.url)} target="_blank" rel="noopener noreferrer">Открыть PDF</a></p>}
      <canvas ref={canvas} role="img" aria-label={`Страница ${page} документа «${file.label}»`}/>
      <p className="sr-only">{pageText}</p>
    </div>
    <p className="document-provenance">{file.derived?'PDF-копия исходного материала. Происхождение и способ преобразования указаны в составе материалов.':'Оригинальный PDF из архива. Содержание файла не изменялось.'}</p>
  </section>;
}
