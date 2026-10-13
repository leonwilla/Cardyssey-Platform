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
          <span className="tcgOverline"><span className="tcgDot"/> CARDYSSEY · TRADING CARD CULTURE</span>
          <h1>Mehr sammeln.<br/><span>Mehr erleben.</span></h1>
          <p>Von deiner Sammlung bis zum nächsten Fund: Cardyssey vereint Sammeln, Entdecken und Shoppen. Die App startet mit Pokémon-Karten – weitere TCGs sollen folgen.</p>
          <div className="tcgHeroButtons"><Link href="/register" className="tcgButton">Zur Cardyssey-App ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum TCG-Shop ↗</a></div>
          <div className="tcgHeroFacts"><span>SAMMLUNG</span><span>·</span><span>SCANNER</span><span>·</span><span>PREISE</span><span>·</span><span>SHOP</span></div>
        </div>
        <div className="v3HeroArtwork" aria-label="Trading Cards aus unterschiedlichen Sammelkartenspielen"><div className="v3HeroGrid"/>
          <span className="v3HeroLabel">THE ART OF COLLECTING <small>001 / CARDYSSEY</small></span>
          <div className="v3Cards">
            <img src={cards[2].src} alt={cards[2].name} className="v3Card v3CardBack" />
            <img src={cards[1].src} alt={cards[1].name} className="v3Card v3CardMid" />
            <img src={cards[0].src} alt={cards[0].name} className="v3Card v3CardFront" />
          </div>
          <span className="v3HeroFoot">MEHR ALS EIN KARTENSPIEL.</span>
        </div>
      </div></section>
      <section className="tcgWrap v3TwoPaths" aria-label="Unsere Angebote">
        <article className="v3Path v3PathApp" id="app"><div className="v3PathCopy"><span className="tcgMiniLabel">01 / DIE APP</span><h2>Deine Sammlung.<br/>Dein Überblick.</h2><p>Die Karten deiner Sammlung erfassen, Varianten verwalten und Sets vervollständigen. Aktuell mit Fokus auf Pokémon.</p><Link href="/collection" className="tcgButton">Web-App entdecken ↗</Link></div>
          <div className="v3Dashboard" aria-label="Vorschau der Cardyssey-Sammlungsfunktionen"><div className="v3DashTop"><strong>Cardyssey</strong><span>COLLECTION</span></div><div className="v3DashHeading"><strong>Meine Karten</strong><span>Sets · Sammlung · Preise</span></div><div className="v3DashCards">{cards.map(c=><div key={c.src}><img src={c.src} alt={c.name}/></div>)}</div><div className="v3DashBottom">DEINE KARTEN. DEIN FORTSCHRITT.</div></div>
        </article>
        <article className="v3Path v3PathStore" id="shop"><div className="v3PathCopy"><span className="tcgMiniLabel">02 / DER SHOP</span><h2>Für deinen<br/>nächsten Fund.</h2><p>Booster, Karten und Zubehör: Entdecke unsere TCG-Welt im Cardyssey-Shop.</p><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Shop besuchen ↗</a></div>
          <div className="v3ShopVisual"><span>THE CARDYSSEY SHOP</span><div className="v3ShopCard"><img src="/landing/cards/swsh12pt5-160.png" alt="Trading Card als Bildbeispiel, kein konkretes Shop-Angebot"/></div><strong>ENTDECKEN.<br/>SAMMELN.<br/>WEITERGEHEN.</strong></div>
        </article>
      </section>
      <section className="tcgWrap v3Features" id="funktionen"><div className="v3SectionTitle"><span className="tcgMiniLabel">ALLES, WAS DU BRAUCHST</span><h2>Eine Plattform.<br/><em>Viele Möglichkeiten.</em></h2></div>
        <div className="v3FeaturesRow"><Link href="/scan"><span>01 / SCANNER</span><h3>Karten scannen.</h3><p>Aktuell Pokémon-Karten erkennen und erfassen.</p><b>↗</b></Link><Link href="/collection"><span>02 / SAMMLUNG</span><h3>Alles an einem Ort.</h3><p>Karten, Sets und Varianten.</p><b>↗</b></Link><Link href="/collection"><span>03 / PREISE</span><h3>Werte im Blick.</h3><p>Verfügbare Preise und Entwicklungen.</p><b>↗</b></Link><Link href="/friends"><span>04 / COMMUNITY</span><h3>Zusammen sammeln.</h3><p>Freunde und Karten teilen.</p><b>↗</b></Link></div>
      </section>
      <section className="tcgWrap v3Roadmap" id="ausblick" aria-labelledby="v3RoadmapTitle">
        <div className="v3RoadmapHead"><div><span className="tcgMiniLabel">CARDYSSEY ENTWICKELT SICH WEITER</span><h2 id="v3RoadmapTitle">Heute Pokémon. <em>Morgen mehr TCG.</em></h2></div><p>Wir bauen Cardyssey Schritt für Schritt zu einem Zuhause für Sammelkartenspiele aus. Was noch fehlt, kennzeichnen wir offen.</p></div>
        <div className="v3RoadmapGrid">
          <div className="v3RoadmapItem v3RoadmapCurrent"><span className="v3RoadmapStatus">● BEREITS VERFÜGBAR</span><strong>Pokémon TCG</strong><p>Sammlung, Kartensuche und Scanner mit Pokémon-Karten.</p></div>
          <div className="v3RoadmapItem"><span className="v3RoadmapStatus">◷ GEPLANT</span><strong>Weitere Kartenspiele</strong><p>Mehr TCG-Kataloge und Sammelmöglichkeiten als zukünftige Erweiterung.</p></div>
          <div className="v3RoadmapItem"><span className="v3RoadmapStatus">◷ IN PLANUNG</span><strong>Trading &amp; Angebote</strong><p>Persönliche Tauschangebote, Wishlist-Abgleich und Wertausgleich.</p></div>
        </div>
        <span className="v3RoadmapFoot">Ausblick, keine Termin- oder Verfügbarkeitszusage.</span>
      </section>
      <section className="v3Community" id="community"><div className="tcgWrap v3CommunityInner"><div><span className="tcgMiniLabel">GEMEINSAM STATT ALLEIN</span><h2>Eine Leidenschaft.<br/><em>Viele Sammler.</em></h2><p>Entdecke Sammlungen, zeig deine Lieblingskarten und bleib mit anderen Sammlern in Kontakt.</p><Link href="/register" className="tcgButton tcgButtonLine">Community entdecken ↗</Link></div><div className="v3CommunityCards"><img src="/landing/cards/sv4-234.png" alt="Pokémon Trading Card"/><img src="/landing/cards/yugioh-dark-magician.jpg" alt="Yu-Gi-Oh! Trading Card"/></div></div></section>
      <section className="tcgWrap v3Bottom"><div><span className="tcgMiniLabel">CARDYSSEY</span><h2>Dein nächster Fund<br/>beginnt hier.</h2></div><div className="v3BottomButtons"><Link href="/register" className="tcgButton">Kostenlos starten ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum Shop ↗</a><a href={ANDROID_APK_DOWNLOAD_URL} className="v3Apk">Android-App herunterladen →</a></div></section>
    </main>
    <footer className="tcgFooter"><div className="tcgWrap tcgFooterInner"><Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link><span>© 2026 Cardyssey</span><nav><a href="https://shop.cardyssey.de">Shop</a><Link href="/impressum">Impressum</Link><Link href="/datenschutz">Datenschutz</Link><Link href="/login">Login</Link></nav></div></footer>
  </div>;
}
