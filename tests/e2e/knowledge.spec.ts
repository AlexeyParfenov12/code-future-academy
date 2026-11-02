import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const knowledge=JSON.parse(fs.readFileSync('public/content/knowledge/index.json','utf8'));
const shots=process.env.CFA_QA_DIR||'test-results/visual';
fs.mkdirSync(shots,{recursive:true});

test('book directories, logical order, search, levels and refresh',async({page})=>{
 await page.goto('/#/textbook');await expect(page.locator('.knowledge-summary')).toContainText('72 глав');
 await expect(page.locator('.knowledge-group-entry')).toHaveCount(7);await expect(page.locator('.knowledge-topic-row')).toHaveCount(0);
 await page.locator('.knowledge-group-entry').filter({hasText:'Начало работы'}).click();
 await expect(page.locator('.knowledge-topic-row').first()).toContainText('Интерпретатор и первый запуск');
 await page.reload();await expect(page.locator('.knowledge-topic-row')).toHaveCount(6);
 await page.getByRole('link',{name:'Все разделы',exact:true}).click();
 await page.getByLabel('Поиск по учебнику').fill('yield');await expect(page.locator('.knowledge-topic-row')).toHaveCount(1);
 await page.getByLabel('Уровень материала').selectOption('intermediate');await page.reload();
 await expect(page.getByLabel('Поиск по учебнику')).toHaveValue('yield');await expect(page.getByLabel('Уровень материала')).toHaveValue('intermediate');
 await page.locator('.knowledge-topic-row').click();await expect(page.locator('h1')).toHaveText('Генераторы и yield');
 await expect(page.locator('.prose')).toContainText('sum исчерпывает генератор');
 await page.locator('.reading-main .code-block').first().getByRole('button',{name:'Скопировать код',exact:true}).click();
 const source=JSON.parse(fs.readFileSync('content/knowledge/chapters/generators.json','utf8')).examples[0].code;
 expect((await page.evaluate(()=>navigator.clipboard.readText())).replace(/\r\n/g,'\n')).toBe(source);
 await expect(page.locator('.topic-prerequisites')).toContainText('Итерируемые объекты');
 await page.locator('.lesson-toc button').filter({hasText:'Границы'}).click();
 await expect(page.locator('.prose h2').filter({hasText:'Границы'})).toBeInViewport();
});

test('AI directory, RAG content, new sources and enriched lesson',async({page,request})=>{
 await page.goto('/#/ai');await expect(page.locator('.knowledge-summary')).toContainText('73 глав');await expect(page.locator('.knowledge-group-entry')).toHaveCount(7);
 await page.locator('.knowledge-group-entry').filter({hasText:'LLM и RAG'}).click();await expect(page.locator('.knowledge-topic-row')).toHaveCount(7);
 await page.locator('.knowledge-topic-row').filter({hasText:'RAG: поиск перед ответом'}).click();
 await expect(page.locator('.reading-main .prose')).toContainText('это не переобучение', {ignoreCase:true});
 await expect(page.locator('.reading-main .prose')).toContainText('Генерации здесь нет');
 await expect(page.locator('.resource-card')).not.toHaveCount(0);
 await page.goto('/#/lesson/M01-L02?tab=extended');
 await expect(page.locator('.extended-lecture')).toContainText('predict_proba',{timeout:15000});
 const errors:string[]=[];
 for(const topic of knowledge.topics){
  const response=await request.get(topic.contentUrl);
  if(!response.ok())errors.push(topic.id);
  else expect((await response.json()).examplesVerified,topic.id).toBe(true);
 }
 expect(errors).toEqual([]);
});

test('resources filter by purpose, type, language and persist through refresh',async({page})=>{
 await page.goto('/#/resources');await expect(page.locator('.knowledge-summary')).toContainText('94 материалов');
 await expect(page.locator('.knowledge-group-entry')).toHaveCount(new Set(knowledge.resources.map((r:{category:string})=>r.category)).size);
 await expect(page.locator('.resource-card')).toHaveCount(0);
 await page.getByLabel('Поиск источника или инструмента').fill('Jupyter');
 await expect(page.locator('.resource-card')).not.toHaveCount(0);
 await page.getByLabel('Тип источника').selectOption('tool');await page.getByLabel('Язык источника').selectOption('EN');
 await page.reload();await expect(page.getByLabel('Поиск источника или инструмента')).toHaveValue('Jupyter');
 await expect(page.locator('.resource-card')).not.toHaveCount(0);
 await expect(page.locator('.resource-card').first()).toContainText('С чего начать:');
 await page.getByRole('button',{name:'Добавить источник',exact:true}).click();
 await page.getByLabel('Название',{exact:true}).fill('Моя документация');
 await page.getByLabel('HTTPS-адрес').fill('https://docs.python.org/3/');
 await page.getByRole('button',{name:'Сохранить ссылку',exact:true}).click();
 await page.getByRole('link',{name:'Все разделы',exact:true}).click();
 await expect(page.locator('.resource-card')).toContainText('Моя документация');
 await page.reload();await expect(page.locator('.resource-card')).toContainText('Моя документация');
});

test('new library layouts fit small screens and both themes',async({page})=>{
 test.setTimeout(90000);
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:960});
  for(const route of ['textbook','ai','textbook/rag','resources?type=tool']){
   await page.goto('/#/'+route);await expect(page.locator('h1')).toBeVisible();
   if(route==='textbook/rag')await expect(page.locator('.reading-main .prose')).toContainText('Генерации здесь нет');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),width+' '+route).toBe(true);
   if(width===390||width===1440)await page.screenshot({path:path.join(shots,'knowledge-'+width+'-'+route.replace(/[/?=]/g,'-')+'.png'),fullPage:true});
  }
 }
 await page.setViewportSize({width:1440,height:1000});await page.goto('/#/textbook/numpy-broadcasting');
 await expect(page.locator('.reading-main .prose')).toContainText('n²');
 await page.getByRole('button',{name:/тёмн/i}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.screenshot({path:path.join(shots,'knowledge-dark.png'),fullPage:true});
});
