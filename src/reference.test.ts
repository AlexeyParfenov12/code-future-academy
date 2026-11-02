import {describe,it,expect,vi,afterEach} from 'vitest';
import {normalizeCode} from './components/CodeBlock';
import {readState} from './state';
import {buildExtendedLecture} from './extended';
import type {Lesson} from './models';
afterEach(()=>vi.unstubAllGlobals());
describe('reference library contracts',()=>{
 it('preserves literal backslash n, indentation and blank lines while normalizing CRLF',()=>{expect(normalizeCode('if ok:\r\n    print("a\\nb")\r\n\r\n')).toBe('if ok:\n    print("a\\nb")\n\n')});
 it('migrates only library preferences from former learning storage',()=>{vi.stubGlobal('localStorage',{getItem:(key:string)=>key==='cfa-learning-v1'?JSON.stringify({theme:'dark',favorites:['M01-L03'],progress:{secret:true},drafts:{secret:true}}):null});const value=readState();expect(value.theme).toBe('dark');expect(value.favorites).toEqual(['M01-L03']);expect(value).not.toHaveProperty('progress');expect(value).not.toHaveProperty('drafts')});
 it('keeps the authored lecture and links its exact official tasks',()=>{const value=buildExtendedLecture({id:'M01-L03',extendedLecture:'## Подробная глава\n\nОбъяснение.',tasks:[{id:'T-stable',number:5,title:'Минуты в секунды'}]} as Lesson);expect(value).toContain('Подробная глава');expect(value).toContain('#/lesson/M01-L03/task/T-stable')});
});
