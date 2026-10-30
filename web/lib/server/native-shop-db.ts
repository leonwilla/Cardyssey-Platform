import "server-only";
import { spawn } from "node:child_process";

/**
 * Transitional DB adapter using the PostgreSQL CLI on the host.
 * No user input is interpolated into SQL. Arguments are encoded as
 * JSON and passed via psql -v, then converted with quote_literal.
 * Disabled unless CARDYSSEY_NATIVE_SHOP_DB_ENABLED=true.
 * A dedicated DB role with privileges on cardyssey_shop only is required.
 */
export async function shopSql(statement: string): Promise<string> {
 if (process.env.CARDYSSEY_NATIVE_SHOP_DB_ENABLED !== "true") throw new Error("native_shop_disabled");
 if (!statement.trim()) throw new Error("empty_sql");
 const url = process.env.CARDYSSEY_SHOP_DATABASE_URL;
 if (!url) throw new Error("shop_db_missing");
 return new Promise((resolve,reject)=>{
  const child=spawn("psql",[url,"-X","-q","-v","ON_ERROR_STOP=1","-A","-t","-c",statement],{stdio:["ignore","pipe","pipe"],env:{...process.env,PGCONNECT_TIMEOUT:"5"}});
  let stdout="",stderr="";
  child.stdout.on("data",(v:Buffer)=>{stdout+=v.toString();if(stdout.length>1_000_000)child.kill()});
  child.stderr.on("data",(v:Buffer)=>{stderr+=v.toString().slice(0,400)});
  child.on("error",()=>reject(new Error("psql_unavailable")));
  child.on("close",code=>code===0?resolve(stdout.trim()):reject(new Error("shop_database_query_failed")));
 });
}
export function sqlLiteral(input: string): string {
 return "'"+input.replaceAll("'","''")+"'";
}
