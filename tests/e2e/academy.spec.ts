import {test,expect,type Page} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const catalog=JSON.parse(fs.readFileSync('public/content/index.json','utf8'));
const lesson=(id:string)=>JSON.parse(fs.readFileSync('public/content/lessons/'+id+'.json','utf8'));
const first=lesson('M01-L03').tasks[0];
const fifth=lesson('M01-L03').tasks.find((t:{number:number})=>t.number===5);
const shots=process.env.CFA_QA_DIR||'test-results/visual';fs.mkdirSync(shots,{recursive:true});
async function snap(page:Page,name:string){await page.evaluate(()=>{(document.activeElement as HTMLElement)?.blur();window.scrollTo({top:0,behavior:'instant'})});await page.screenshot({path:path.join(shots,name),fullPage:true})}

test('all 74 routes, modules and material requests',async({page,request})=>{
 test.setTimeout(120000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('h1')).toHaveText('Code Future Academy.');await expect(page.locator('.module-entry')).toHaveCount(5);
 await snap(page,'home-desktop.png');
 for(const m of catalog.modules){await page.goto('/#/module/'+m.id);await expect(page.locator('h1')).toContainText(m.title)}
 for(const l of catalog.lessons){await page.goto('/#/lesson/'+l.id+'?tab=tasks');await expect(page.locator('h1').first()).toHaveText(l.title);expect((await request.get('/content/lessons/'+l.id+'.json')).ok()).toBeTruthy()}
 expect(errors).toEqual([]);
});

test('number search, immediate code, exact clipboard and expanded links',async({page})=>{
 await page.goto('/');await page.getByLabel('Глобальный поиск').fill('1.3 №5');await expect(page.locator('.search-results a')).toHaveCount(1);await page.locator('.search-results a').click();
 await expect(page.locator('h1')).toHaveText(fifth.title);await expect(page.locator('.solution-section .code-block')).toBeVisible();await expect(page.locator('.solution-explanation')).not.toHaveAttribute('open');
 await page.locator('.solution-section').getByRole('button',{name:'Скопировать код',exact:true}).click();expect(await page.evaluate(()=>navigator.clipboard.readText().then(t=>t.replace(/\r\n?/g,'\n')))).toBe(fifth.solution.code.replace(/\r\n?/g,'\n'));
 await expect(page.getByRole('link',{name:'Открыть задание на iSMART'})).toHaveAttribute('href',fifth.ismartLink.candidateUrl);await expect(page.locator('.official')).toContainText('ещё не проверена');
 await page.getByText('Подробное объяснение',{exact:true}).click();await expect(page.locator('.line-explanations')).toBeVisible();await snap(page,'answer-desktop.png');
 await page.goto('/#/lesson/M01-L03?tab=extended');await expect(page.locator('.extended-lecture')).toContainText('input');await page.locator('.extended-lecture a[href*="/task/"]').first().click();await expect(page.locator('.solution-section')).toBeVisible();
 await page.getByLabel('Глобальный поиск').fill('Переменные');await page.locator('.search-results a[href*="/textbook/variables"]').click();await expect(page.locator('h1')).toHaveText('Переменные');
});

test('text clipboard and downloadable project',async({page,request})=>{
 const t=lesson('M04-L13').tasks[0];await page.goto('/#/lesson/M04-L13/task/'+t.id);await page.getByRole('button',{name:'Скопировать ответ',exact:true}).click();expect(await page.evaluate(()=>navigator.clipboard.readText().then(t=>t.replace(/\r\n?/g,'\n')))).toBe(t.solution.answer);
 const link=page.getByRole('link',{name:/Скачать самостоятельный пример/});await expect(link).toBeVisible();expect((await request.get((await link.getAttribute('href'))!)).ok()).toBeTruthy();
});

test('native and converted PDF paging, zoom, download and fullscreen',async({page,request})=>{
 for(const id of ['M01-L03','M02-L17']){
  await page.goto('/#/lesson/'+id+'?tab=lecture');await expect(page.locator('.pdf-viewport')).toHaveAttribute('aria-busy','false',{timeout:30000});await expect(page.locator('.document-error')).toHaveCount(0);
  expect(await page.locator('.pdf-viewport canvas').evaluate((c:HTMLCanvasElement)=>c.width)).toBeGreaterThan(200);
  await page.getByRole('button',{name:'Следующая страница PDF'}).click();await expect(page.getByLabel('Страница PDF',{exact:true})).toHaveValue('2');await page.getByRole('button',{name:'Увеличить PDF'}).click();await expect(page.getByRole('button',{name:'125%'})).toBeVisible();
  expect((await request.get((await page.getByRole('link',{name:'Скачать PDF',exact:true}).getAttribute('href'))!)).ok()).toBeTruthy();
  await page.getByRole('button',{name:'PDF на весь экран'}).click();await expect(page.locator('.document-reader')).toHaveClass(/reader-fullscreen/);await page.getByRole('button',{name:'Выйти из полноэкранного PDF'}).click();await snap(page,id+'-pdf.png');
 }
});

test('original presentation PDF, keyboard, PPTX, missing originals and CSV preview',async({page,request})=>{
 await page.goto('/#/lesson/M01-L03?tab=slides');await expect(page.locator('.pdf-viewport')).toHaveAttribute('aria-busy','false');await expect(page.locator('.document-title')).toContainText('Оригинальная презентация iSMART');
 await page.locator('.pdf-viewport').focus();await page.keyboard.press('ArrowRight');await expect(page.getByLabel('Страница PDF',{exact:true})).toHaveValue('2');
 for(const name of ['Скачать оригинальную презентацию PPTX','Скачать PDF'])expect((await request.get((await page.getByRole('link',{name,exact:true}).getAttribute('href'))!)).ok()).toBeTruthy();
 await page.goto('/#/lesson/M04-L01?tab=slides');await expect(page.locator('.presentation-missing')).toContainText('не обнаружен');await expect(page.locator('.document-reader')).toHaveCount(0);await page.getByRole('button',{name:'Читать исходную лекцию'}).click();await expect(page.locator('.document-reader')).toBeVisible();
 await page.goto('/#/lesson/M01-L12?tab=files');await page.getByText(/Посмотреть первые/).first().click();await expect(page.locator('table').first()).toBeVisible();
});

test('solutions are grouped by module and lesson and survive refresh and back',async({page})=>{
 await page.goto('/#/practice');await expect(page.locator('.solution-module-entry')).toHaveCount(4);await expect(page.locator('.practice-card')).toHaveCount(0);await expect(page.locator('.pagination')).toHaveCount(0);
 await page.locator('.solution-module-entry').filter({hasText:'Python'}).click();await expect(page).toHaveURL(/module=1/);await expect(page.locator('.solution-lesson-entry')).toHaveCount(13);
 await page.locator('.solution-lesson-entry').filter({hasText:'Первые программы'}).click();await expect(page).toHaveURL(/lesson=M01-L03/);await expect(page.locator('.task-card')).toHaveCount(8);
 await page.reload();await expect(page.locator('.task-card')).toHaveCount(8);await expect(page.locator('h1')).toContainText('Занятие 1.3');
 await page.locator('.task-card').first().click();await expect(page.locator('.solution-section')).toBeVisible();await page.goBack();await expect(page.locator('.task-card')).toHaveCount(8);await expect(page).toHaveURL(/lesson=M01-L03/);
 await page.getByRole('link',{name:'Все занятия модуля',exact:true}).click();await expect(page.locator('.solution-lesson-entry')).toHaveCount(13);
 await snap(page,'solutions-lessons.png');
});

test('migration, bookmarks, theme, excluded routes',async({page,request})=>{
 await page.addInitScript(()=>{if(!localStorage.getItem('seeded')){localStorage.setItem('cfa-learning-v1',JSON.stringify({theme:'light',favorites:[],progress:{secret:true},drafts:{secret:true}}));localStorage.setItem('cfa-draft-test','old');localStorage.setItem('seeded','yes')}});
 await page.goto('/#/lesson/M01-L03');await page.getByRole('button',{name:'Добавить в избранное',exact:true}).click();await page.getByRole('button',{name:'Включить тёмную тему'}).click();await page.reload();await expect(page.getByRole('button',{name:'Убрать из избранного',exact:true})).toBeVisible();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 const local=await page.evaluate(()=>({value:JSON.parse(localStorage.getItem('cfa-reference-v2')!),old:localStorage.getItem('cfa-learning-v1'),draft:localStorage.getItem('cfa-draft-test')}));expect(local.value.progress).toBeUndefined();expect(local.value.drafts).toBeUndefined();expect(local.old).toBeNull();expect(local.draft).toBeNull();
 await page.goto('/#/favorites');await expect(page.locator('.lesson-row-main')).toContainText('Первые программы');await snap(page,'dark-favorites.png');
 for(const route of ['/lab','/progress','/lesson/M01-C1-4','/lesson/M01-L03/task/M01-L03-A01']){await page.goto('/#'+route);await expect(page.locator('h1')).toBeVisible();await expect(page.locator('.solution-section')).toHaveCount(0)}
 expect((await (await request.get('/content/lessons/M01-C1-4.json')).text()).includes('"tasks"')).toBeFalsy();
});

test('six screen widths, menu, light and dark reading',async({page})=>{
 test.setTimeout(120000);
 for(const width of [320,375,390,768,1024,1440]){
  await page.setViewportSize({width,height:900});
  for(const route of ['/','/#/catalog','/#/practice','/#/practice?module=1','/#/practice?module=1&lesson=M01-L03','/#/lesson/M01-L03/task/'+first.id,'/#/lesson/M01-L03?tab=extended','/#/lesson/M01-L03?tab=lecture','/#/lesson/M01-L03?tab=slides','/#/import-report']){await page.goto(route);await expect(page.locator('h1').first()).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth),width+' '+route).toBeLessThanOrEqual(1)}
 }
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByRole('button',{name:'Открыть меню'}).click();await page.locator('.sidebar').getByRole('link',{name:'Готовые решения',exact:true}).click();await expect(page.locator('h1')).toContainText('Готовые решения');
 await page.goto('/');await snap(page,'home-mobile.png');await page.goto('/#/lesson/M01-L03/task/'+first.id);await page.getByRole('button',{name:'Включить тёмную тему'}).click();await snap(page,'answer-mobile-dark.png');
});


test('assessment navigation: eight controls, four intermediate documents and final defense',async({page})=>{
 await page.goto('/#/assessments');await expect(page.locator('h1')).toHaveText('Контроли и аттестации.');await expect(page.locator('.assessment-control')).toHaveCount(8);await expect(page.locator('.assessment-assessment')).toHaveCount(4);await expect(page.locator('.assessment-final')).toHaveCount(1);
 for(const link of await page.locator('.assessment-control a').all()){await expect(link).toHaveAttribute('href',/^https:\/\/edu.future.ismart.org\/course\/practice\/0\/unit\/[a-z0-9]+\/element\/[a-z0-9]+$/)}
 await page.getByRole('navigation',{name:'Модули контролей и аттестаций'}).getByRole('link',{name:'Модуль 1',exact:true}).click();await expect(page.locator('.assessment-entry')).toHaveCount(3);await page.reload();await expect(page.locator('.assessment-entry')).toHaveCount(3);
 await page.locator('.assessment-assessment').getByRole('link',{name:'Открыть документы'}).click();await expect(page.locator('h1')).toHaveText('Промежуточная аттестация');await expect(page.locator('.document-reader')).toBeVisible();
 await page.goto('/#/assessments?module=5');await page.getByRole('link',{name:'Открыть документы'}).click();await expect(page.locator('h1')).toHaveText('Защита итогового проекта');
 await page.goto('/#/lesson/M01-C1-4');await expect(page).toHaveURL(/assessments\?module=1/);
 for(const width of [320,390,1440]){await page.setViewportSize({width,height:900});await page.goto('/#/assessments');await expect(page.locator('.assessment-entry')).toHaveCount(13);expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)}
 await snap(page,'assessments-desktop.png');
});
