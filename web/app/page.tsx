import Image from "next/image";
import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { ANDROID_APK_DOWNLOAD_URL } from "@/lib/android-release";
import "./landing-editorial.css";

const cards = [
  { src: "/landing/cards/base1-4.png", name: "Charizard · Base Set" },
  { src: "/landing/cards/yugioh-dark-magician.jpg", name: "Yu-Gi-Oh! · Dark Magician (Bildbeispiel)" },
  { src: "/landing/cards/sv4-234.png", name: "Pokémon TCG · Paradox Rift" },
];
export default function Home() {
  return <div className="tcgHome v3">
    <header className="tcgHeader"><div className="tcgWrap tcgHeaderInner">
      <Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link>
      <nav className="tcgNav" aria-label="Hauptnavigation"><a href="#app">Die App</a><a href="#shop">Der Shop</a><a href="#funktionen">Funktionen</a><a href="#community">Community</a><a href="#ausblick">Ausblick</a></nav>
      <div className="tcgHeaderActions"><Link href="/login" className="tcgLogin">Anmelden</Link><Link href="/register" className="tcgButton tcgButtonSmall">Kostenlos starten ↗</Link></div>
    </div></header>
    <main>
      <section className="tcgHero" id="plattform"><div className="tcgWrap tcgHeroGrid">
        <div className="tcgHeroCopy">
          <span className="tcgOverline"><span className="tcgDot"/> DEIN HOBBY. DEINE KARTEN.</span>
          <h1>Für alle, die<br/><span>Karten lieben.</span></h1>
          <p>Sammlung organisieren, Lieblingskarten entdecken und im Shop stöbern. Ein Ort für deine Leidenschaft – ganz gleich, wie groß deine Sammlung ist.</p>
          <div className="tcgHeroButtons"><Link href="/register" className="tcgButton">Zur Cardyssey-App ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum TCG-Shop ↗</a></div>
          <div className="tcgHeroFacts"><span>SAMMLUNG</span><span>·</span><span>SCANNER</span><span>·</span><span>PREISE</span><span>·</span><span>SHOP</span></div>
        </div>
        <div className="v3HeroArtwork" aria-label="Trading Cards aus unterschiedlichen Sammelkartenspielen"><div className="v3HeroGrid"/>
          <span className="v3HeroLabel">KARTEN, DIE BEGEISTERN <small>TCG & COLLECTING</small></span>
          <div className="v3Cards">
            <Image width={320} height={448} src={cards[2].src} alt={cards[2].name} className="v3Card v3CardBack" />
            <Image width={320} height={448} src={cards[1].src} alt={cards[1].name} className="v3Card v3CardMid" />
            <Image width={320} height={448} src={cards[0].src} alt={cards[0].name} className="v3Card v3CardFront" />
          </div>
          <span className="v3HeroFoot">MEHR ALS EIN KARTENSPIEL.</span>
        </div>
      </div></section>
      <section className="tcgWrap v5AppSpotlight" id="app">
        <div className="v5AppText"><span className="tcgMiniLabel">DIE CARDYSSEY APP</span><h2>Deine Sammlung verdient mehr als eine Tabelle.</h2><p>Scanne deine Karten, verwalte Varianten und behalte den Überblick über Sets und verfügbare Marktpreise. Aktuell für Pokémon TCG.</p><div className="v5Bullet"><span>Sammlung & Sets</span><span>Scanner</span><span>Preisübersicht</span><span>Freunde & Chat</span></div><Link href="/register" className="tcgButton">App kostenlos ausprobieren ↗</Link></div>
        <div className="v5RealScreen v5CardPreview"><span className="v5ScreenTop">Deine Karten im Mittelpunkt <small>TCG-Sammlung</small></span><div className="v5PreviewCards"><Image width={320} height={448} src="/landing/cards/base1-4.png" alt="Pokémon Glurak Karte"/><Image width={320} height={448} src="/landing/cards/yugioh-dark-magician.jpg" alt="Yu-Gi-Oh! Dark Magician Karte"/><Image width={320} height={448} src="/landing/cards/sv4-234.png" alt="Pokémon TCG Sammelkarte"/></div><span className="v5ScreenFoot">Kartenillustration · Echte App-Aufnahmen folgen</span></div>
      </section>
      <section className="v5ShopFeature" id="shop"><div className="tcgWrap v5ShopFeatureGrid">
        <div className="v5ShopGallery"><div className="v5ShopCard v5ShopCardA"><Image width={320} height={448} src="/landing/cards/yugioh-dark-magician.jpg" alt="Yu-Gi-Oh! Sammelkarte"/></div><div className="v5ShopCard v5ShopCardB"><Image width={320} height={448} src="/landing/cards/sv3-223.png" alt="Pokémon Sammelkarte"/></div></div>
        <div className="v5ShopCopy"><span className="tcgMiniLabel">DER CARDYSSEY SHOP</span><h2>Ein guter Fund fühlt sich besonders an.</h2><p>Trading Cards und Zubehör entdecken. Ein Shop für unterschiedliche TCG-Welten, mit Raum für neue Spiele und Produkte.</p><a className="tcgButton" href="https://shop.cardyssey.de/">Shop entdecken ↗</a></div>
      </div></section>
      <section className="tcgWrap v3Features" id="funktionen"><div className="v3SectionTitle"><span className="tcgMiniLabel">FÜR DEINEN SAMMLERALLTAG</span><h2>Eine Plattform.<br/><em>Viele Möglichkeiten.</em></h2></div>
        <div className="v3FeaturesRow"><Link href="/scan"><span>SCANNER</span><h3>Karten scannen.</h3><p>Aktuell Pokémon-Karten erkennen und erfassen.</p><b>↗</b></Link><Link href="/collection"><span>SAMMLUNG</span><h3>Alles an einem Ort.</h3><p>Karten, Sets und Varianten.</p><b>↗</b></Link><Link href="/collection"><span>MARKTPREISE</span><h3>Werte im Blick.</h3><p>Verfügbare Preise und Entwicklungen.</p><b>↗</b></Link><Link href="/friends"><span>COMMUNITY</span><h3>Zusammen sammeln.</h3><p>Freunde und Karten teilen.</p><b>↗</b></Link></div>
      </section>
      <section className="tcgWrap v3Roadmap" id="ausblick" aria-labelledby="v3RoadmapTitle">
        <div className="v3RoadmapHead"><div><span className="tcgMiniLabel">CARDYSSEY ENTWICKELT SICH WEITER</span><h2 id="v3RoadmapTitle">Hier fängt es an. <em>Und wächst weiter.</em></h2></div><p>Wir bauen Cardyssey Schritt für Schritt zu einem Zuhause für Sammelkartenspiele aus. Was noch fehlt, kennzeichnen wir offen.</p></div>
        <div className="v3RoadmapGrid">
          <div className="v3RoadmapItem v3RoadmapCurrent"><span className="v3RoadmapStatus">VERFÜGBAR</span><strong>Pokémon TCG</strong><p>Sammlung, Kartensuche und Scanner mit Pokémon-Karten.</p></div>
          <div className="v3RoadmapItem"><span className="v3RoadmapStatus">COMING SOON</span><strong>Weitere Kartenspiele</strong><p>Mehr TCG-Kataloge und Sammelmöglichkeiten als zukünftige Erweiterung.</p></div>
          <div className="v3RoadmapItem"><span className="v3RoadmapStatus">IN PLANUNG</span><strong>Trading &amp; Angebote</strong><p>Persönliche Tauschangebote, Wishlist-Abgleich und Wertausgleich.</p></div>
        </div>
        <span className="v3RoadmapFoot">Ausblick, keine Termin- oder Verfügbarkeitszusage.</span>
      </section>
      <section className="v3Community" id="community"><div className="tcgWrap v3CommunityInner"><div><span className="tcgMiniLabel">GEMEINSAM STATT ALLEIN</span><h2>Eine Leidenschaft.<br/><em>Viele Sammler.</em></h2><p>Entdecke Sammlungen, zeig deine Lieblingskarten und bleib mit anderen Sammlern in Kontakt.</p><Link href="/register" className="tcgButton tcgButtonLine">Community entdecken ↗</Link></div><div className="v3CommunityCards"><Image width={320} height={448} src="/landing/cards/sv4-234.png" alt="Pokémon Trading Card"/><Image width={320} height={448} src="/landing/cards/yugioh-dark-magician.jpg" alt="Yu-Gi-Oh! Trading Card"/></div></div></section>
      <section className="tcgWrap v3Bottom"><div><span className="tcgMiniLabel">CARDYSSEY</span><h2>Dein nächster Fund<br/>beginnt hier.</h2></div><div className="v3BottomButtons"><Link href="/register" className="tcgButton">Kostenlos starten ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum Shop ↗</a><a href={ANDROID_APK_DOWNLOAD_URL} className="v3Apk">Android-App herunterladen →</a></div></section>
    </main>
    <footer className="tcgFooter"><div className="tcgWrap tcgFooterInner"><Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link><span>© 2026 Cardyssey</span><nav><a href="https://shop.cardyssey.de">Shop</a><Link href="/impressum">Impressum</Link><Link href="/datenschutz">Datenschutz</Link><Link href="/login">Login</Link></nav></div></footer>
  </div>;
}
