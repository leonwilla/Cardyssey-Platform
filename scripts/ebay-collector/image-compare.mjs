#!/usr/bin/env node
// Compare public eBay thumbnails with canonical German TCGdex card scans.
// Dry-run evidence only. Caller decides whether to import.
import sharp from '../../web/node_modules/sharp/dist/index.cjs';
import fs from 'node:fs';

const allowed=(value,kind)=>{
 try {
  const url=new URL(value);
  if(url.protocol!=='https:'||url.username||url.password||url.port||url.searchParams.has('url'))return false;
  if(kind==='listing')return url.hostname==='i.ebayimg.com'||url.hostname.endsWith('.ebayimg.com');
  return url.hostname==='assets.tcgdex.net';
 } catch{return false;}
};
async function fetchImage(url,kind){
 if(!allowed(url,kind))throw Error('UNTRUSTED_URL');
 for(let i=0;i<3;i++){
  const r=await fetch(url,{redirect:'manual',signal:AbortSignal.timeout(9000),headers:{'User-Agent':'CardysseyImageIdentityAudit/1.0'}});
  if(r.status>=300&&r.status<400){const next=new URL(r.headers.get('location')||'',url).href;if(!allowed(next,kind))throw Error('UNTRUSTED_REDIRECT');url=next;continue;}
  if(!r.ok)throw Error(`HTTP_${r.status}`);
  const len=Number(r.headers.get('content-length')||0);if(len>2500000)throw Error('TOO_LARGE');
  const data=Buffer.from(await r.arrayBuffer());if(data.length>2500000)throw Error('TOO_LARGE');
  const meta=await sharp(data,{limitInputPixels:12e6}).metadata();
  if(meta.width<100||meta.height<100)throw Error('SMALL_IMAGE');
  return data;
 }
 throw Error('REDIRECT_LOOP');
}
async function features(data){
 const {data:buf,info}=await sharp(data,{limitInputPixels:12e6}).resize(64,88,{fit:'fill'}).removeAlpha().raw().toBuffer({resolveWithObject:true});
 const a=new Float64Array(info.width*info.height);
 for(let i=0;i<a.length;i++){const r=buf[i*3],g=buf[i*3+1],b=buf[i*3+2];a[i]=r*.299+g*.587+b*.114;}
 const edge=[];const colors=[];
 for(let y=2;y<86;y+=2)for(let x=2;x<62;x+=2){const i=y*64+x;
  // Multi-scale edge features handle camera exposure changes better than raw pixels.
  edge.push(a[i+1]-a[i-1],a[i+64]-a[i-64],a[i+2]-a[i-2],a[i+128]-a[i-128]);
  const index=i*3;colors.push(buf[index]/255,buf[index+1]/255,buf[index+2]/255);
 }
 return {edge,colors};
}
function similarity(a,b){
 let xy=0,xx=0,yy=0;for(let i=0;i<a.length;i++){xy+=a[i]*b[i];xx+=a[i]*a[i];yy+=b[i]*b[i];}
 return Math.max(-1,Math.min(1,xy/(Math.sqrt(xx*yy)||1)));
}
async function evaluate(ref,listing){
 const reference=await features(ref),photo=await features(listing);
 const edge=similarity(reference.edge,photo.edge);
 // Image-based identity score, not evidence of the card's condition or foil.
 return {edge:Math.round(edge*10000)/10000};
}
async function main(){
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const ref=await fetchImage(input.reference,'reference');
 const negatives=[];
 for(const url of (input.negativeReferences||[]).slice(0,2)){
  try{negatives.push(await features(await fetchImage(url,'reference')))}catch{}
 }
 const refFeatures=await features(ref);
 const items=[];
 for(const item of (input.items||[]).slice(0,30)){
  try {
   const photo=await features(await fetchImage(item.url,'listing'));
   const edge=similarity(refFeatures.edge,photo.edge);
   const competitor=negatives.length?Math.max(...negatives.map(n=>similarity(n.edge,photo.edge))):null;
   const gap=competitor===null?null:edge-competitor;
   items.push({id:item.id,edge:Math.round(edge*10000)/10000,
     competingEdge:competitor===null?null:Math.round(competitor*10000)/10000,
     margin:gap===null?null:Math.round(gap*10000)/10000,
     verified:edge>=0.88 && gap!==null && gap>=0.15});
  }
  catch(e){items.push({id:item.id,error:String(e.message||e).slice(0,60)});}
 }
 process.stdout.write(JSON.stringify({items}));
}
main().catch(e=>{process.stderr.write(String(e.message||e));process.exitCode=1;});
