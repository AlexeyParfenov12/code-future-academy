import type {Catalog,Lesson} from './models';
export async function getJSON<T>(path:string, signal?:AbortSignal):Promise<T> {const r=await fetch(path,{signal});if(!r.ok)throw new Error('Не удалось загрузить материал. Попробуйте обновить страницу.');return r.json() as Promise<T>}
export const getCatalog=()=>getJSON<Catalog>('/content/index.json');
const cache=new Map<string,Lesson>();
export async function getLesson(id:string, signal?:AbortSignal){if(cache.has(id))return cache.get(id)!;const l=await getJSON<Lesson>(`/content/lessons/${encodeURIComponent(id)}.json`,signal);cache.set(id,l);return l}
