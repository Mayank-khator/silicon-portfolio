import {readdir,readFile,writeFile,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
const blocks=[];const seen=new Set();
async function inspect(dir){let meta;try{meta=JSON.parse(await readFile(join(dir,'package.json'),'utf8'));}catch{return;}const key=`${meta.name}@${meta.version}`;if(seen.has(key))return;seen.add(key);const files=await readdir(dir);for(const name of files.filter(n=>/^(licen[sc]e|copying|notice)(\.|$)/i.test(n))){try{blocks.push(`\n${'='.repeat(70)}\n${key} — ${name}\n${'='.repeat(70)}\n${await readFile(join(dir,name),'utf8')}`);}catch{}}}
const dirs=await readdir('node_modules/.pnpm',{withFileTypes:true});
for(const dir of dirs.filter(d=>d.isDirectory()&&d.name!=='node_modules')){const base=join('node_modules/.pnpm',dir.name,'node_modules');let packages;try{packages=await readdir(base,{withFileTypes:true});}catch{continue;}for(const entry of packages){if(entry.name.startsWith('@')){for(const n of await readdir(join(base,entry.name)))await inspect(join(base,entry.name,n));}else await inspect(join(base,entry.name));}}
await mkdir('apps/web/public',{recursive:true});await writeFile('apps/web/public/third-party-licenses.txt','Third-party dependency license texts. Generated from installed package files.\n'+blocks.join('\n'));
console.log(`Collected ${blocks.length} license/notice files from ${seen.size} installed packages.`);
