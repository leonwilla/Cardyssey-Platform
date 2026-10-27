import Link from "next/link";
import Image from "next/image";
import "../redesign.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

type Product = {
  id: number;
  name: string;
  permalink: string;
  images?: { src: string; alt: string }[];
  prices?: { price: string; currency_code: string; currency_minor_unit: number };
  is_in_stock?: boolean;
};

const shopUrl = process.env.NEXT_PUBLIC_SHOP_URL || "https://shop.cardyssey.de";

async function products(): Promise<Product[] | null> {
  try {
    const endpoint = new URL("/", shopUrl);
    endpoint.searchParams.set("rest_route", "/wc/store/v1/products");
    endpoint.searchParams.set("per_page", "12");
    const response = await fetch(endpoint, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!response.ok || !(response.headers.get("content-type") || "").includes("json")) return null;
    const result: unknown = await response.json();
    return Array.isArray(result) ? result : null;
  } catch {
    return null;
  }
}

function euro(product: Product) {
  const p = product.prices;
  if (!p || !/^\d+$/.test(p.price) || !Number.isInteger(p.currency_minor_unit)) return null;
  const number = Number(p.price) / Math.pow(10, p.currency_minor_unit);
  if (!Number.isFinite(number)) return null;
  try { return new Intl.NumberFormat("de-DE", { style: "currency", currency: p.currency_code }).format(number); }
  catch { return null; }
}

function safeLink(permalink: string) {
  try {
    const target = new URL(permalink);
    return target.origin === new URL(shopUrl).origin ? target.href : shopUrl;
  } catch { return shopUrl; }
}

const categories = [
  { name: "Einzelkarten", note: "Karten für deine Sammlung" },
  { name: "Booster & Displays", note: "Versiegelte TCG-Produkte" },
  { name: "Figuren & Plüsch", note: "Sammlerstücke und Geschenke" },
  { name: "Zubehör", note: "Hüllen und Aufbewahrung" },
];

export default async function ShopDesignPreview() {
  const items = await products();
  return (
    <div className="cardysseyRedesign min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-5 py-12 md:px-8 md:py-20">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <span className="text-sm font-semibold uppercase tracking-widest text-primary">Cardyssey Shop · Neues Design</span>
          <Link href={shopUrl} className="text-sm underline underline-offset-4">Zum bisherigen WooCommerce-Shop</Link>
        </div>
        <section className="mt-8 grid items-center gap-8 md:grid-cols-2 md:gap-14">
          <div>
            <h1 className="font-serif text-5xl leading-tight md:text-7xl">Alles für deine <em className="text-primary">Sammlung.</em></h1>
            <p className="mt-6 text-lg text-muted-foreground">Karten, Booster und Zubehör – entdecke das Cardyssey-Sortiment im neuen Look.</p>
            <a href="#produkte" className="mt-8 inline-flex rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground">Produkte entdecken</a>
          </div>
          <div className="relative aspect-[4/3] overflow-hidden rounded-3xl bg-paper-deep">
            <Image src="/landing/cards/base1-4.png" alt="Beispiel einer Sammelkarte" fill className="object-contain p-8" sizes="(min-width:768px) 45vw,90vw"/>
          </div>
        </section>
        <section aria-label="Produktkategorien" className="mt-16">
          <h2 className="font-serif text-4xl">Kategorien</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {categories.map(c => <a href="#produkte" key={c.name} className="rounded-2xl border border-border bg-card p-6 transition-colors hover:border-primary">
              <h3 className="font-serif text-xl">{c.name}</h3>
              <p className="mt-3 text-sm text-muted-foreground">{c.note}</p>
            </a>)}
          </div>
        </section>
        <section id="produkte" className="mt-20 scroll-mt-24">
          <h2 className="font-serif text-4xl">Aktuelles Sortiment</h2>
          {items === null ? <p className="mt-5 text-muted-foreground">Das Sortiment lässt sich derzeit nicht abrufen. <Link href={shopUrl} className="underline">Im bisherigen Shop ansehen.</Link></p>
          : items.length === 0 ? <p className="mt-5 text-muted-foreground">Aktuell sind noch keine Produkte im Shop verfügbar.</p>
          : <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {items.map(product => <a key={product.id} href={safeLink(product.permalink)} className="group overflow-hidden rounded-3xl border border-border bg-card transition-colors hover:border-primary">
                <div className="flex aspect-[4/3] items-center justify-center bg-paper-deep p-4">
                  {product.images?.[0]?.src ? <img className="h-full w-full object-contain" alt={product.images[0].alt || product.name} src={product.images[0].src} loading="lazy"/> : <span className="text-sm text-muted-foreground">Kein Produktbild</span>}
                </div>
                <div className="p-6">
                  <h3 className="font-serif text-xl">{product.name}</h3>
                  <p className="mt-3 font-semibold text-primary">{euro(product) ?? "Preis im Shop ansehen"}</p>
                  <p className="mt-3 text-sm text-muted-foreground">{product.is_in_stock === false ? "Nicht auf Lager" : "Im Shop ansehen →"}</p>
                </div>
              </a>)}
            </div>}
        </section>
        <p className="mt-14 border-t border-border pt-6 text-sm text-muted-foreground">Diese zweite Designvariante zeigt echte verfügbare WooCommerce-Produkte. Warenkorb, Checkout und Bestellungen bleiben bis zur Umstellung im bisherigen Shop.</p>
      </main>
      <SiteFooter />
    </div>
  );
}
