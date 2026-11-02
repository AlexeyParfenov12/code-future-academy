// Browser layout preflight for generated, script-free SVGs. Does not execute archive code.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';
const base=path.resolve('public/content');
const files=fs.readdirSync(path.join(base,'slides'),{withFileTypes:true}).flatMap(d=>fs.readdirSync(path.join(base,'slides',d.name)).map(f=>path.join(base,'slides',d.name,f)));
const digest=f=>createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const previousPath=path.join(base,'slide-render-report.json');
const previous=fs.existsSync(previousPath)?JSON.parse(fs.readFileSync(previousPath,'utf8')):null;
if(previous&&files.length===Object.keys(previous.hashes).length&&files.every(f=>previous.hashes[path.relative(base,f).replaceAll('\\','/')]===digest(f))){console.log(`Slide preflight unchanged: ${files.length} slides, ${previous.adjustedBlocks} text boxes fitted.`);process.exit(0)}
let browser;
try{browser=await chromium.launch({...(process.platform==='win32'?{channel:'msedge'}:{}),headless:true})}
catch{throw new Error('Slide QA needs a browser. Install Microsoft Edge on Windows, or run npx playwright install chromium.')}
const page=await browser.newPage();const adjustments=[];let remaining=[];
try{
for(let start=0;start<files.length;start+=35){
 const batch=files.slice(start,start+35);
 await page.setContent('<html><body>'+batch.map((f,i)=>'<section data-slide="'+i+'">'+fs.readFileSync(f,'utf8')+'</section>').join('')+'</body></html>');
 const result=await page.evaluate(()=>{
  const changes=[];const changed=new Set();const unresolved=[];
  for(const section of document.querySelectorAll('[data-slide]')){
   let boxIndex=0;
   for(const box of section.querySelectorAll('foreignObject > div')){
    const originalH=box.scrollHeight;let factor=1;let attempts=0;
    while((box.scrollHeight>box.clientHeight+2||box.scrollWidth>box.clientWidth+2)&&attempts<8){
     const ratio=Math.min(box.clientHeight/box.scrollHeight,box.clientWidth/box.scrollWidth,.99)*.99;
     for(const span of box.querySelectorAll('span'))span.style.fontSize=(parseFloat(span.style.fontSize)*ratio).toFixed(3)+'px';
     for(const p of box.querySelectorAll('p')){p.style.marginTop=parseFloat(getComputedStyle(p).marginTop)*ratio+'px';p.style.marginBottom=parseFloat(getComputedStyle(p).marginBottom)*ratio+'px'}
     factor*=ratio;attempts++;
    }
    if(attempts){changes.push({index:Number(section.dataset.slide),box:boxIndex,fontScale:Number(factor.toFixed(4)),previousHeight:originalH,availableHeight:box.clientHeight});changed.add(Number(section.dataset.slide))}
    if(box.scrollHeight>box.clientHeight+2||box.scrollWidth>box.clientWidth+2)unresolved.push({index:Number(section.dataset.slide),box:boxIndex});
    boxIndex++;
   }
  }
  return {changes,unresolved,modified:[...changed].map(i=>({index:i,svg:document.querySelector('[data-slide="'+i+'"] svg').outerHTML}))};
 });
 for(const item of result.modified)fs.writeFileSync(batch[item.index],item.svg);
 adjustments.push(...result.changes.map(c=>({...c,file:path.relative(base,batch[c.index]).replaceAll('\\','/')})));
 remaining.push(...result.unresolved);
}
}finally{await browser.close()}
if(remaining.length)throw new Error(`${remaining.length} overflowing slide boxes remain.`);
const report={renderer:'DrawingML geometry and rich text → script-free SVG; browser text fitting',slideCount:files.length,adjustedBlocks:adjustments.length,overflowingBlocks:remaining.length,adjustments,hashes:Object.fromEntries(files.map(f=>[path.relative(base,f).replaceAll('\\','/'),digest(f)]))};
fs.writeFileSync(previousPath,JSON.stringify(report,null,2)+'\n');
const importReportPath=path.join(base,'import-report.json');const importReport=JSON.parse(fs.readFileSync(importReportPath,'utf8'));importReport.rendering={renderer:report.renderer,slideCount:report.slideCount,adjustedBlocks:report.adjustedBlocks,overflowingBlocks:report.overflowingBlocks};fs.writeFileSync(importReportPath,JSON.stringify(importReport,null,2)+'\n');
console.log(JSON.stringify({slides:files.length,adjustedBlocks:adjustments.length,overflowingBlocks:remaining.length}));
