import {createContext,useContext,useEffect,useState} from 'react';
import type {ReactNode} from 'react';
import type {Catalog,Resource} from './models';
export interface LocalState {favorites:string[];completed:string[];recent:string[];last:string|null;theme:'light'|'dark';resources:Resource[];checklist:string[]}
const empty:LocalState={favorites:[],completed:[],recent:[],last:null,theme:'light',resources:[],checklist:[]};
export function readState():LocalState {try{const d=JSON.parse(localStorage.getItem('cfa-learning-v1')||'{}');return {...empty,...d,favorites:Array.isArray(d.favorites)?d.favorites:[],completed:Array.isArray(d.completed)?d.completed:[],recent:Array.isArray(d.recent)?d.recent:[],resources:Array.isArray(d.resources)?d.resources:[],checklist:Array.isArray(d.checklist)?d.checklist:[]}}catch{return empty}}
type Store={catalog:Catalog;local:LocalState;toggle:(field:'favorites'|'completed'|'checklist',id:string)=>void;visit:(id:string)=>void;theme:()=>void;saveResource:(r:Resource)=>void;notice:string;toast:(s:string)=>void;storageAvailable:boolean};
const Context=createContext<Store|null>(null);
export function Provider({catalog,children}:{catalog:Catalog;children:ReactNode}){const [local,setLocal]=useState(readState);const [notice,setNotice]=useState('');const [storageAvailable,setStorageAvailable]=useState(true);
useEffect(()=>{document.documentElement.dataset.theme=local.theme;try{localStorage.setItem('cfa-learning-v1',JSON.stringify(local));setStorageAvailable(true)}catch{setStorageAvailable(false)}},[local]);
useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),2600);return()=>clearTimeout(t)},[notice]);
function toggle(field:'favorites'|'completed'|'checklist',id:string){setLocal(s=>({...s,[field]:s[field].includes(id)?s[field].filter(v=>v!==id):[...s[field],id]}))}
function visit(id:string){setLocal(s=>s.last===id&&s.recent[0]===id?s:{...s,last:id,recent:[id,...s.recent.filter(v=>v!==id)].slice(0,12)})}
return <Context.Provider value={{catalog,local,toggle,visit,theme:()=>setLocal(s=>({...s,theme:s.theme==='light'?'dark':'light'})),saveResource:r=>setLocal(s=>({...s,resources:[...s.resources,r]})),notice,toast:setNotice,storageAvailable}}>{children}</Context.Provider>}
export function useStore(){const c=useContext(Context);if(!c)throw new Error('Missing context');return c}
