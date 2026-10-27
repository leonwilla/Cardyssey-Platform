import Link from "next/link";
import "../../redesign.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

type Category = { id:number; name:string; slug:string; parent:number; count:number; image?:{src:string;alt:string}|null };
const shop = process.env.NEXT_PUBLIC_SHOP_URL || "https://shop.cardyssey.de";

async function categories():Promise<Category[]> {
  try {
    const url=new URL("/",shop);
    url.searchParams.set("rest_route","/wc/store/v1/products/categories");
    url.searchParams.set("per_page","100");
    const response=await fetch(url,{cache:"no-store",signal:AbortSignal.timeout(8000)});
    if(!response.ok || !(response.headers.get("content-type")||"").includes("json"))return [];
    const result:unknown=await response.json();
    if(!Array.isArray(result))return [];
    return result.filter((c):c is Category=>!!c&&typeof c.id==="number"&&typeof c.name==="string"&&typeof c.slug==="string");
  }catch{return []}
}
export default async function ShopSetsPage(){
  const list=await categories();
  const group=list.find(c=>/^(pokémon[ -]?)?sets$|erweiterungen/i.test(c.name));
  const sets=group ? list.filter(c=>c.parent===group.id) : list.filter(c=>c.parent!==0 && /set|edition|erweiterung/i.test(list.find(p=>p.id===c.parent)?.name||""));
  return <div className="cardysseyRedesign min-h-screen">
    <SiteHeader/>
    <main className="mx-auto max-w-7xl px-5 py-12 md:px-8 md:py-20">
      <Link href="/preview-shop" className="text-sm underline underline-offset-4">← Zur Shop-Übersicht</Link>
      <p className="mt-10 text-sm font-semibold uppercase tracking-widest text-primary">Pokémon · Einzelkarten</p>
      <h1 className="mt-4 font-serif text-5xl md:text-7xl">Nach Set <em className="text-primary">stöbern.</em></h1>
      <p className="mt-5 max-w-2xl text-lg text-muted-foreground">Wähle eine Erweiterung, um die verfügbaren Karten dieses Sets im Shop anzusehen.</p>
      {sets.length ? <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {sets.map(set=><a key={set.id} href={new URL("/product-category/"+encodeURIComponent(set.slug)+"/",shop).href} className="overflow-hidden rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary">
          <div className="flex aspect-[4/3] items-center justify-center rounded-xl bg-paper-deep">
            {set.image?.src ? <img src={set.image.src} alt={set.image.alt||""} loading="lazy" className="h-full max-w-full object-contain p-4"/> : <span className="text-5xl text-muted-foreground">✦</span>}
          </div>
          <h2 className="mt-5 font-serif text-xl">{set.name}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{set.count} Produkte · Einzelkarten ansehen →</p>
        </a>)}
      </div>:<div className="mt-12 rounded-2xl border border-border bg-card p-8">
        <h2 className="font-serif text-2xl">Die Set-Kategorien werden vorbereitet</h2>
        <p className="mt-3 text-muted-foreground">Im WooCommerce-Shop müssen die Erweiterungen als Unterkategorien von „Sets“ angelegt und den Einzelkarten zugeordnet werden. Hier erscheinen anschließend automatisch die echten Sets – ohne erfundene Karten oder Angebote.</p>
        <a href={shop} className="mt-5 inline-flex rounded-full bg-primary px-5 py-3 font-semibold text-primary-foreground">Bisherigen Shop öffnen</a>
      </div>}
    </main><SiteFooter/>
  </div>;
}
