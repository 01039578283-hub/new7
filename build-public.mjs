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
    if(e.isDirectory())walk(rel,accept);else if(accept(e.name,rel))copy(rel);
  }
};
for(const dir of ['전국학원','과목별학원','학습가이드','상담문의','지점안내','선생님찾기','교육정보','학습커리큘럼'])walk(dir,n=>n.endsWith('.html'));
const extensions=new Set(['.css','.js','.jpg','.jpeg','.png','.gif','.webp','.avif','.svg','.ico','.woff','.woff2','.ttf','.mp4','.webm']);
const guideManifest=JSON.parse(fs.readFileSync(path.join(root,'learning-guides.json'),'utf8'));
const guideSlugs=guideManifest.guides.map(g=>g.slug);
if(guideSlugs.length!==49 || new Set(guideSlugs).size!==49)throw new Error('Learning guide manifest mismatch');
const teacherManifest=JSON.parse(fs.readFileSync(path.join(root,'teacher-directory.json'),'utf8'));
const teacherBranches=teacherManifest.branches;
if(teacherBranches.length!==205 || new Set(teacherBranches.map(b=>b.path)).size!==205 || teacherBranches.reduce((n,b)=>n+b.profiles.length,0)!==1002)throw new Error('Teacher profile manifest mismatch');
const educationManifest=JSON.parse(fs.readFileSync(path.join(root,'education-info.json'),'utf8'));
const educationArticles=educationManifest.articles;
if(educationArticles.length!==30 || new Set(educationArticles.map(a=>a.path)).size!==30 || educationArticles.some(a=>a.images.length!==3) || new Set(educationArticles.flatMap(a=>a.images.map(i=>i.path))).size!==90)throw new Error('Education article/image manifest mismatch');
const curriculumManifest=JSON.parse(fs.readFileSync(path.join(root,'curriculum-data.json'),'utf8'));
const curriculumPages=curriculumManifest.pages;
if(curriculumPages.length!==80 || new Set(curriculumPages.map(p=>p.path)).size!==80 || curriculumManifest.subjects.length!==66 || curriculumManifest.grades.length!==12 || curriculumManifest.levels.length!==45 || curriculumManifest.electives.length!==29)throw new Error('Curriculum manifest mismatch');
const worksheets=new Set(guideSlugs.map(slug=>`assets/learning-guides/records/${slug}.txt`));
walk('assets',(n,rel)=>extensions.has(path.extname(n).toLowerCase()) || worksheets.has(rel.replaceAll('\\','/')));
for(const name of ['index.html','sitemap.xml','rss.xml','robots.txt','llms.txt'])copy(name);
for(const name of fs.readdirSync(root))if(/^(?:google|naver)[a-z0-9]+\.html$/i.test(name))copy(name);
const expected=(fs.readFileSync(path.join(root,'sitemap.xml'),'utf8').match(/<loc>/g)||[]).length;
if(pages!==expected || pages!==8755+guideSlugs.length+teacherBranches.length+1+educationArticles.length+1+curriculumPages.length)throw new Error(`Page inventory mismatch: ${pages}/${expected}`);
for(const curriculum of curriculumPages)if(!fs.existsSync(path.join(output,curriculum.path.slice(1),'index.html')))throw new Error(`Missing curriculum: ${curriculum.path}`);
for(const article of educationArticles) {
  if(!fs.existsSync(path.join(output,article.path.slice(1),'index.html')))throw new Error(`Missing education article: ${article.path}`);
  for(const picture of article.images)if(!fs.existsSync(path.join(output,picture.path.slice(1))))throw new Error(`Missing education image: ${picture.path}`);
}
if(!fs.existsSync(path.join(output,'교육정보','index.html')))throw new Error('Missing education hub');
for(const branch of teacherBranches) {
  if(!fs.existsSync(path.join(output,branch.path.slice(1), 'index.html')))throw new Error(`Missing teacher branch: ${branch.path}`);
  for(const profile of branch.profiles)if(!fs.existsSync(path.join(output,profile.photo.slice(1))))throw new Error(`Missing teacher image: ${profile.photo}`);
}
for(const slug of guideSlugs) {
  if(!fs.existsSync(path.join(output,'학습가이드',slug,'index.html')))throw new Error(`Missing guide: ${slug}`);
  if(!fs.existsSync(path.join(output,'assets','learning-guides','records',slug+'.txt')))throw new Error(`Missing worksheet: ${slug}`);
}
console.log(JSON.stringify({files,pages,privateSourcesIncluded:false,output}));
