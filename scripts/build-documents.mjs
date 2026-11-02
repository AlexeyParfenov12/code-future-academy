// Convert source documents to PDF; never execute code embedded in course content.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {chromium} from '@playwright/test';
import {createHighlighterCore} from 'shiki/core';
import {createJavaScriptRegexEngine} from 'shiki/engine/javascript';
import python from 'shiki/langs/python.mjs';
import theme from 'shiki/themes/github-dark.mjs';

const argument=process.argv.indexOf('--sources');
if(argument<0)throw new Error('Pass --sources <private document-sources.json>.');
const sources=JSON.parse(fs.readFileSync(process.argv[argument+1],'utf8'));
const root=path.resolve('public/content');const directory=path.join(root,'documents');fs.mkdirSync(directory,{recursive:true});
const reportPath=path.join(root,'document-report.json');const previous=fs.existsSync(reportPath)?JSON.parse(fs.readFileSync(reportPath,'utf8')):{documents:[]};
const sha=value=>createHash('sha256').update(value).digest('hex');
const previousMap=new Map(previous.documents.map(document=>[document.id,document]));const completed=[];
const highlighter=await createHighlighterCore({langs:[python],themes:[theme],engine:createJavaScriptRegexEngine()});
const browser=await chromium.launch({...(process.platform==='win32'?{channel:'msedge'}:{}),headless:true});
const page=await browser.newPage();
const css=`@page{size:A4;margin:20mm 18mm 22mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#172b3b;font-size:11pt;line-height:1.65;margin:0}h1{font-size:23pt;line-height:1.3;margin:12mm 0 8mm;letter-spacing:-.4pt}h2{font-size:17pt;line-height:1.4;margin:10mm 0 5mm}h3{font-size:14pt;line-height:1.4;margin:8mm 0 4mm}h4{font-size:12pt;margin:6mm 0 3mm}h1,h2,h3,h4{break-after:avoid}p{margin:0 0 4mm;orphans:3;widows:3}li{margin:2mm 0}a{color:#087f8c;text-decoration:none}table{border-collapse:collapse;width:100%;margin:5mm 0;font-size:9pt;line-height:1.5;table-layout:fixed;overflow-wrap:anywhere}th,td{padding:2.8mm;border:1px solid #d9e3e9;vertical-align:top}th{background:#edf4f5;text-align:left}tr{break-inside:avoid}code{font-family:Consolas,'Courier New',monospace;font-size:9.5pt}p code,li code{color:#087f8c;background:#edf4f5;padding:.4mm 1mm}pre{padding:4mm 5mm;border-radius:1.5mm;font-size:9pt;line-height:1.55;white-space:pre-wrap;overflow-wrap:break-word;background:#101820;color:#e0ebf0;margin:5mm 0;break-inside:avoid}pre code{font-size:9pt}.code-sample{break-inside:avoid}.code-sample pre{font-size:9pt}.pdf-meta{border-top:2px solid #087f8c;padding-top:4mm;font-size:9pt;color:#637785;line-height:1.6}.pdf-meta strong{color:#087f8c}.source-label{font-size:9pt;color:#6a7f8a;margin-top:3mm}blockquote{border-left:2px solid #087f8c;padding-left:4mm;margin:5mm 0;color:#4e6974}img{max-width:100%}`;

function markdownHtml(markdown){
  return renderToStaticMarkup(React.createElement(ReactMarkdown,{remarkPlugins:[remarkGfm],skipHtml:true,components:{
    pre:({children})=>{
      const child=Array.isArray(children)?children[0]:children;
      const props=React.isValidElement(child)?child.props:{};const code=String(props.children||'').replace(/\n$/,'');const language=props.className?.replace('language-','');
      if(language==='python')return React.createElement('div',{className:'code-sample',dangerouslySetInnerHTML:{__html:highlighter.codeToHtml(code,{lang:'python',theme:'github-dark'})}});
      return React.createElement('pre',null,code);
    },a:({children})=>React.createElement('span',null,children)
  }},markdown));
}

function metadata(file,name,label,source,derived,pages){
  return {url:'/content/documents/'+path.basename(file),name,label,format:'pdf',derived,pageCount:pages,sha256:sha(fs.readFileSync(file)),source};
}

try{
for(const source of sources){
  const lessonPath=path.join(root,'lessons',source.lessonId+'.json');const lesson=JSON.parse(fs.readFileSync(lessonPath,'utf8'));lesson.documents||={};
  for(const kind of ['lecture','presentation']){
    const target=path.join(directory,source.lessonId+'-'+kind+'.pdf');const id=source.lessonId+'-'+kind;
    if(kind==='presentation'){
      const original=source.originalPresentation;
      if(!original){if(fs.existsSync(target))fs.unlinkSync(target);delete lesson.documents.presentation;continue}
      if(!fs.existsSync(original.pdfCache))throw new Error(source.lessonId+': run scripts/render-original-presentations.ps1 first. A prepared replacement will not be used.');
      fs.copyFileSync(original.pdfCache,target);
      const record={id,lessonId:source.lessonId,kind,derived:true,sourceFormat:'pptx',renderer:'Microsoft PowerPoint PDF export',sourceSha256:original.sha256,sha256:sha(fs.readFileSync(target)),file:path.basename(target),source:original.name};
      completed.push(record);
      lesson.documents.presentation=metadata(target,source.title+' — оригинальная презентация.pdf','Оригинальная презентация iSMART — PDF-копия',{path:original.name,sha256:original.sha256},true,original.slideCount);
      continue;
    }
    let content,sourceHash,derived=true,label;
    if(kind==='lecture'&&source.originalPdf){
      content=fs.readFileSync(source.originalPdf);sourceHash=sha(content);derived=false;label='Оригинальная лекция';
    }else if(kind==='lecture'){
      content=source.originalHTML||source.originalMarkdown.replace(/^.*https?:\/\/\S*(?:teacher|back=)\S*.*$/gm,'').replace(/^Источник:.*$/gm,'');sourceHash=sha(content);label='PDF-версия исходной лекции';
    }else{
      content=source.slidePaths.map(file=>fs.readFileSync(file.startsWith('/content/')?path.join(root,file.slice('/content/'.length)):file,'utf8'));sourceHash=sha(content.join('\n'));label='Презентация — PDF-копия';
    }
    const last=previousMap.get(id);
    if(!(last&&last.sourceSha256===sourceHash&&fs.existsSync(target)&&sha(fs.readFileSync(target))===last.sha256)){
      if(kind==='lecture'&&!derived)fs.writeFileSync(target,content);
      else if(kind==='lecture'){
        const meta='<div class="pdf-meta"><strong>CODE FUTURE ACADEMY / '+source.lessonId+'</strong><br/>PDF-версия исходной лекции iSMART из '+(source.originalHTML?'сохранённого HTML':'исходного Markdown')+'. Содержание не заменено пересказом. Служебные элементы интерфейса исключены.</div>';
        const printOverrides='.cc-lesson{max-width:none!important;padding:0!important;margin:0!important;font-size:11pt!important;line-height:1.65!important}.original-lecture-part+ .original-lecture-part{break-before:page}table,.cc-table{min-width:0!important;width:100%!important;table-layout:fixed!important}th,td{overflow-wrap:anywhere!important;font-size:9pt!important;padding:2mm!important}.cc-table-wrapper{overflow:visible!important}pre{white-space:pre-wrap!important;overflow-wrap:anywhere!important;max-width:100%!important}svg{max-width:100%}h1,h2,h3,h4{break-after:avoid}tr{break-inside:avoid}';
        await page.setContent('<!doctype html><html lang="ru"><meta charset="utf-8"/><style>'+css+'</style><body>'+meta+(source.originalHTML?content:markdownHtml(content))+'<style>'+printOverrides+'</style></body></html>');
        await page.pdf({path:target,format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font:9px Arial;color:#71818a;width:100%;text-align:center">Code Future Academy · '+source.lessonId+' · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
      }else{
        await page.setContent('<!doctype html><html><meta charset="utf-8"/><style>@page{size:1280px 720px;margin:0}html,body{margin:0;padding:0}section{width:1280px;height:720px;break-after:page;overflow:hidden}section:last-child{break-after:auto}svg{display:block;width:1280px;height:720px}</style><body>'+content.map(svg=>'<section>'+svg+'</section>').join('')+'</body></html>');
        await page.pdf({path:target,width:'1280px',height:'720px',printBackground:true,preferCSSPageSize:true});
      }
    }
    const record={id,lessonId:source.lessonId,kind,derived,sourceFormat:kind==='lecture'?(source.originalPdf?'pdf':source.originalHTML?'html':'markdown'):'pptx',sourceSha256:sourceHash,sha256:sha(fs.readFileSync(target)),file:path.basename(target),source:kind==='lecture'?(source.originalPdf?source.originalPdfLabel||path.basename(source.originalPdf):source.originalHTML?'Снимки страниц.json / '+source.htmlElements.join(', '):source.folder+'/Лекция по слайдам.md'):source.folder+'/Презентация — итоговая.pptx'};
    completed.push(record);
    lesson.documents[kind]=metadata(target,source.title+(kind==='lecture'?' — лекция.pdf':' — презентация.pdf'),label,{path:record.source,sha256:record.sourceSha256},derived,kind==='presentation'?source.slidePaths.length:undefined);
  }
  fs.writeFileSync(lessonPath,JSON.stringify(lesson,null,2)+'\n');
}
}finally{await browser.close();highlighter.dispose()}
fs.writeFileSync(reportPath,JSON.stringify({lecturePdfs:completed.filter(d=>d.kind==='lecture').length,originalPdfs:completed.filter(d=>!d.derived).length,presentationPdfs:completed.filter(d=>d.kind==='presentation').length,missingOriginalPresentations:sources.filter(s=>!s.originalPresentation).map(s=>s.lessonId),htmlConversions:completed.filter(d=>d.sourceFormat==='html').length,conversion:'Исходный PDF без изменений; исходный HTML (с таблицами и схемами) или Markdown → PDF; оригинальные вложения PPTX iSMART → штатный экспорт Microsoft PowerPoint → PDF. Подготовленные владельцем презентации исключены.',documents:completed},null,2)+'\n');
console.log(JSON.stringify({documents:completed.length,originalPdfs:completed.filter(d=>!d.derived).length}));
