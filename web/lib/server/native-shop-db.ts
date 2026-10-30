import "server-only";
import {spawn} from "node:child_process";

/** Native shop PostgreSQL adapter. Only loopback, never external SQL input. */
export async function shopSql(statement:string):Promise<string>{
 if(process.env.CARDYSSEY_NATIVE_SHOP_DB_ENABLED!=="true")throw Error("native_shop_disabled");
 const raw=process.env.CARDYSSEY_SHOP_DATABASE_URL;
 if(!raw)throw Error("shop_database_unconfigured");
 const url=new URL(raw);
 if(url.protocol!=="postgresql:"||url.hostname!=="127.0.0.1"||url.port!=="5433")throw Error("invalid_db_host");
 return await new Promise<string>((resolve,reject)=>{
  const child=spawn("psql",["-X","-q","-v","ON_ERROR_STOP=1","-A","-t","-c",statement],{
   stdio:["ignore","pipe","pipe"],
   env:{...process.env,PGCONNECT_TIMEOUT:"5",PGHOST:"127.0.0.1",PGPORT:"5433",PGUSER:decodeURIComponent(url.username),PGPASSWORD:decodeURIComponent(url.password),PGDATABASE:decodeURIComponent(url.pathname.slice(1))}
  });
  let out="";
  child.stdout.on("data",(v:Buffer)=>{out+=v.toString();if(out.length>1000000)child.kill()});
  child.stderr.on("data",()=>{});
  child.on("error",()=>reject(Error("psql_unavailable")));
  child.on("close",code=>code===0?resolve(out.trim()):reject(Error("shop_query_failed")));
 });
}
export const sqlLiteral=(v:string)=>"'"+v.replaceAll("'","''")+"'";
