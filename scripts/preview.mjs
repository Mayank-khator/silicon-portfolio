import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
const root=resolve('apps/web/out');
const basePath=(process.env.BASE_PATH||'').replace(/\/+$/,'');
if(basePath&&!/^\/[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*$/.test(basePath))throw new Error('BASE_PATH must be empty or a URL path such as /silicon-portfolio.');
const port=Number(process.env.PORT||3000);
if(!Number.isInteger(port)||port<0||port>65535)throw new Error('PORT must be an integer between 0 and 65535.');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon','.txt':'text/plain'};
const server=http.createServer(async(req,res)=>{try{
  const url=new URL(req.url,'http://localhost');
  let pathname=decodeURIComponent(url.pathname);
  if(basePath&&pathname===basePath){res.writeHead(308,{Location:basePath+'/'+url.search});res.end();return;}
  if(basePath&&!pathname.startsWith(basePath+'/')){res.writeHead(404);res.end('Not found');return;}
  if(basePath)pathname=pathname.slice(basePath.length);
  let path=resolve(root,'.'+pathname);
  if(path!==root&&!path.startsWith(root+sep)){res.writeHead(403);res.end();return;}
  if((await stat(path)).isDirectory())path=resolve(path,'index.html');
  const bytes=await readFile(path);
  res.writeHead(200,{'Content-Type':types[extname(path)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Cache-Control':'no-cache'});res.end(bytes);
}catch{res.writeHead(404);res.end('Not found');}});
server.listen(port,'127.0.0.1',()=>console.log(`Silicon Portfolio preview: http://127.0.0.1:${server.address().port}${basePath}/`));
