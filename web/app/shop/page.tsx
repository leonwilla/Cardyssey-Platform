import { AppShell } from "@/components/AppShell";

export default function ShopPage() {
  const shopUrl = "https://shop.cardyssey.de";
  return (
    <AppShell active="/shop">
      <section className="pageIntro"><div><span className="eyebrowText">Shop</span><h1>Cards & Collectibles</h1><p>WooCommerce bleibt das Backend. Dieses Frontend wird später Produkte und Warenkorb direkt über die Shop-API laden.</p></div></section>
      <section className="shopHero"><div><span className="eyebrowText">Headless WooCommerce</span><h2>Ein Shop, derselbe Look.</h2><p>Produkte, Lager und Bestellungen bleiben in WooCommerce. Nutzer sehen nur unsere eigene Oberfläche.</p><a className="primaryButton inline" href={shopUrl} target="_blank">WooCommerce aktuell öffnen</a></div><div className="shopOrb" /></section>
    </AppShell>
  );
}
