/** Only web output is published. Private facts, spreadsheets and backups stay local. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(root, '.public-release');
if (fs.existsSync(output)) throw new Error('Archive the previous validated output before building a fresh release.');
fs.mkdirSync(output);
let files=0, pages=0;
const copy = rel => {
  const src=path.join(root,rel), dest=path.join(output,rel);
  if (fs.lstatSync(src).isSymbolicLink()) throw new Error('Symlink in public assets');
  fs.mkdirSync(path.dirname(dest),{recursive:true});fs.copyFileSync(src,dest);files++;
  if (path.basename(rel)==='index.html') pages++;
};
const walk = (dir,accept) => {
  for (const e of fs.readdirSync(path.join(root,dir),{withFileTypes:true})) {
    if(e.name.startsWith('.') || e.isSymbolicLink()) continue;
    const rel=path.join(dir,e.name);
    if(e.isDirectory())walk(rel,accept);else if(accept(e.name))copy(rel);
  }
};
for(const dir of ['전국학원','과목별학원','학습가이드','상담문의','지점안내'])walk(dir,n=>n.endsWith('.html'));
const extensions=new Set(['.css','.js','.jpg','.jpeg','.png','.gif','.webp','.avif','.svg','.ico','.woff','.woff2','.ttf','.mp4','.webm']);
walk('assets',n=>extensions.has(path.extname(n).toLowerCase()));
for(const name of ['index.html','sitemap.xml','rss.xml','robots.txt','llms.txt'])copy(name);
for(const name of fs.readdirSync(root))if(/^(?:google|naver)[a-z0-9]+\.html$/i.test(name))copy(name);
const expected=(fs.readFileSync(path.join(root,'sitemap.xml'),'utf8').match(/<loc>/g)||[]).length;
if(pages!==expected || pages!==8755)throw new Error(`Page inventory mismatch: ${pages}/${expected}`);
console.log(JSON.stringify({files,pages,privateSourcesIncluded:false,output}));
