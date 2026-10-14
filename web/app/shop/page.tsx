import { AppShell } from "@/components/AppShell";

type ShopProduct = {
  id: number;
  name: string;
  permalink: string;
  images?: { src: string; alt: string }[];
  prices?: { price: string; currency_code: string; currency_minor_unit: number };
  is_in_stock?: boolean;
};

const shopUrl = process.env.NEXT_PUBLIC_SHOP_URL || "https://shop.cardyssey.de";

async function loadProducts(): Promise<ShopProduct[] | null> {
  try {
    // Query routing also works when WordPress pretty permalinks are disabled.
    const url = new URL("/", shopUrl);
    url.searchParams.set("rest_route", "/wc/store/v1/products");
    url.searchParams.set("per_page", "12");
    url.searchParams.set("orderby", "date");
    url.searchParams.set("order", "desc");
    const response = await fetch(url, { next: { revalidate: 300 }, signal: AbortSignal.timeout(10_000) });
    if (!response.ok) return null;
    const data = await response.json();
    return Array.isArray(data) ? data : null;
  } catch {
    return null;
  }
}

function productPrice(product: ShopProduct) {
  const prices = product.prices;
  if (!prices || !/^\d+$/.test(prices.price) || !Number.isInteger(prices.currency_minor_unit)) return null;
  const amount = Number(prices.price) / 10 ** prices.currency_minor_unit;
  if (!Number.isFinite(amount) || amount < 0) return null;
  try {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency: prices.currency_code }).format(amount);
  } catch {
    return null;
  }
}

function productLink(product: ShopProduct) {
  try {
    const url = new URL(product.permalink);
    return url.origin === new URL(shopUrl).origin ? url.href : shopUrl;
  } catch {
    return shopUrl;
  }
}

export default async function ShopPage() {
  const products = await loadProducts();
  return (
    <AppShell active="/shop">
      <section className="pageIntro"><div><span className="eyebrowText">Shop</span><h1>Cards & Collectibles</h1><p>Entdecke das aktuelle Cardyssey-Sortiment. Warenkorb und Bestellung findest du direkt im Shop.</p></div></section>
      <section className="shopHero"><div><span className="eyebrowText">Cardyssey Shop</span><h2>Für deine Sammlung.</h2><p>Sammelkarten und Zubehör an einem Ort.</p><a className="primaryButton inline" href={shopUrl}>Zum Shop</a></div><div className="shopOrb" /></section>
      {products === null ? (
        <div className="statusPanel">Das Sortiment konnte gerade nicht geladen werden. <a href={shopUrl}>Shop direkt öffnen →</a></div>
      ) : products.length === 0 ? (
        <div className="statusPanel">Unser Sortiment wird gerade vorbereitet. Neue Artikel erscheinen hier automatisch, sobald sie verfügbar sind.</div>
      ) : (
        <section className="cardGrid" aria-label="Aktuelles Sortiment">
          {products.map((product) => (
            <a className="cardTile" href={productLink(product)} key={product.id}>
              {product.images?.[0]?.src && <img src={product.images[0].src} alt={product.images[0].alt || product.name} loading="lazy" style={{ width: "100%", height: 200, objectFit: "contain" }} />}
              <strong>{product.name}</strong>
              <p>{productPrice(product) ?? "Preis im Shop ansehen"}</p>
              <span>{product.is_in_stock === false ? "Aktuell nicht auf Lager" : "Im Shop ansehen →"}</span>
            </a>
          ))}
        </section>
      )}
    </AppShell>
  );
}
