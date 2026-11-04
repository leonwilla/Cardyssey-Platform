// Expansion identifiers encode their release eras; preserve numeric order within each era.
// This is a fallback for the shop's stock-only catalog, which has no release-date field.
const setEraOrder:Record<string,number>={base:1,jungle:1,fossil:1,neo:2,ecard:3,ex:4,dp:5,pl:6,hgss:7,bw:8,xy:9,sm:10,swsh:11,sv:12,me:13};
export function setChronology(id:string){
 const value=id.toLowerCase();
 if(value==='30th'||value==='30th-c'||value==='mep')return 14000;
 const era=Object.keys(setEraOrder).filter(prefix=>value.startsWith(prefix)).sort((a,b)=>b.length-a.length)[0];
 if(!era)return -1;
 const suffix=value.slice(era.length);
 const number=Number.parseInt(suffix.match(/^\d+/)?.[0]||'0',10);
 return setEraOrder[era]*1000+number;
}
