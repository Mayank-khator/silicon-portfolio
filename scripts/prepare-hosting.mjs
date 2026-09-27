import {cp,rm,stat} from 'node:fs/promises';
import {resolve,dirname,basename} from 'node:path';
const root=resolve('.'),source=resolve(root,'apps/web/out'),destination=resolve(root,'out');
// Only replace the known generated export under this repository.
if(dirname(destination)!==root||basename(destination)!=='out'||!(await stat(resolve(source,'index.html'))).isFile())throw new Error('Invalid export paths');
await rm(destination,{recursive:true,force:true});
await cp(source,destination,{recursive:true});
console.log('Prepared static hosting export in out/');
