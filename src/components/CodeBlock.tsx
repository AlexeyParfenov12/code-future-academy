import {useEffect,useState} from 'react';
import {Check,Copy} from 'lucide-react';
import {useStore} from '../state';

export const normalizeCode=(code:string)=>code.replace(/\r\n?/g,'\n');

export function CopyButton({value,label='Скопировать код'}:{value:string;label?:string}) {
  const [copied,setCopied]=useState(false);const {toast}=useStore();
  async function copy(){
    let success=false;
    try{await navigator.clipboard.writeText(value);success=true}catch{
      const field=document.createElement('textarea');field.value=value;field.readOnly=true;
      field.style.cssText='position:fixed;left:-9999px;top:0';document.body.append(field);field.select();
      try{success=document.execCommand('copy')}catch{}finally{field.remove()}
    }
    if(success){setCopied(true);toast(label==='Скопировать ответ'?'Ответ скопирован':label==='Скопировать вывод'?'Вывод скопирован':'Код скопирован с исходными отступами');setTimeout(()=>setCopied(false),2200)}
    else toast('Копирование недоступно. Выделите исходный текст и нажмите Ctrl+C.');
  }
  return <button className={'copy-button '+(copied?'is-copied':'')} onClick={copy}>{copied?<Check size={16}/>:<Copy size={16}/>}<span>{copied?'Скопировано':label}</span></button>;
}

export function CodeBlock({code,language='python',activeLine,label,variant='code'}:{code:string;language?:string;activeLine?:number;label?:string;variant?:'code'|'output'|'error'|'terminal'}) {
  const source=normalizeCode(code);
  const [tokens,setTokens]=useState<{content:string;color?:string}[][]|null>(null);
  useEffect(()=>{
    let live=true;setTokens(null);
    if(['python','py'].includes(language))import('../highlight').then(module=>module.highlight(source)).then(result=>{if(live)setTokens(result)}).catch(()=>{});
    return()=>{live=false};
  },[source,language]);
  const kind=variant==='code'&&language==='text'?'output':variant;
  return <div className={'code-block code-'+kind}>
    <div className="code-toolbar"><span><i/>{label||(kind==='output'?'Результат программы':kind==='error'?'Исходный код с ошибкой':kind==='terminal'?'Команда терминала':'Python')}</span><CopyButton value={source} label={kind==='output'?'Скопировать вывод':'Скопировать код'}/></div>
    <pre tabIndex={0} aria-label={label||'Программный код'}><code>{source.split('\n').map((line,i)=><span key={i} className={'code-line '+(activeLine===i+1?'current-line':'')}><span className="line-number" aria-hidden="true">{i+1}</span><span className="line-source">{tokens?.[i]?tokens[i].map((token,j)=><span key={j} style={{color:token.color}}>{token.content}</span>):line||' '}</span></span>)}</code></pre>
    {activeLine&&<div className="code-foot">Текущая строка: {activeLine}</div>}
  </div>;
}

export function TextAnswer({answer,label='Готовый ответ'}:{answer:string;label?:string}) {
  return <div className="text-answer"><div className="answer-toolbar"><strong>{label}</strong><CopyButton value={answer} label="Скопировать ответ"/></div><pre>{answer}</pre></div>;
}
