import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { ANDROID_APK_DOWNLOAD_URL } from "@/lib/android-release";
import "./landing-editorial.css";

const cards = [
  { src: "/landing/cards/base1-4.png", name: "Charizard · Base Set" },
  { src: "/landing/cards/sv3-223.png", name: "Pokémon TCG · Obsidian Flames" },
  { src: "/landing/cards/sv4-234.png", name: "Pokémon TCG · Paradox Rift" },
];
export default function Home() {
  return <div className="tcgHome v3">
    <header className="tcgHeader"><div className="tcgWrap tcgHeaderInner">
      <Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link>
      <nav className="tcgNav" aria-label="Hauptnavigation"><a href="#app">Die App</a><a href="#shop">Der Shop</a><a href="#funktionen">Funktionen</a><a href="#community">Community</a></nav>
      <div className="tcgHeaderActions"><Link href="/login" className="tcgLogin">Anmelden</Link><Link href="/register" className="tcgButton tcgButtonSmall">Kostenlos starten ↗</Link></div>
    </div></header>
    <main>
      <section className="tcgHero" id="plattform"><div className="tcgWrap tcgHeroGrid">
        <div className="tcgHeroCopy">
          <span className="tcgOverline"><span className="tcgDot"/> CARDYSSEY · POKÉMON TCG</span>
          <h1>Mehr sammeln.<br/><span>Mehr erleben.</span></h1>
          <p>Deine Karten scannen, die Sammlung im Blick behalten und neue Highlights entdecken. Alles rund um dein Hobby – mit App und eigenem Shop.</p>
          <div className="tcgHeroButtons"><Link href="/register" className="tcgButton">Zur Cardyssey-App ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum TCG-Shop ↗</a></div>
          <div className="tcgHeroFacts"><span>SAMMLUNG</span><span>·</span><span>SCANNER</span><span>·</span><span>PREISE</span><span>·</span><span>SHOP</span></div>
        </div>
        <div className="v3HeroArtwork" aria-label="Echte Pokémon-TCG-Karten aus verschiedenen Sets"><div className="v3HeroGrid"/>
          <span className="v3HeroLabel">THE ART OF COLLECTING <small>001 / CARDYSSEY</small></span>
          <div className="v3Cards">
            <img src={cards[2].src} alt={cards[2].name} className="v3Card v3CardBack" />
            <img src={cards[1].src} alt={cards[1].name} className="v3Card v3CardMid" />
            <img src={cards[0].src} alt={cards[0].name} className="v3Card v3CardFront" />
          </div>
          <span className="v3HeroFoot">ECHTE KARTEN. ECHTE SAMMLUNGEN.</span>
        </div>
      </div></section>
      <section className="tcgWrap v3TwoPaths" aria-label="Unsere Angebote">
        <article className="v3Path v3PathApp" id="app"><div className="v3PathCopy"><span className="tcgMiniLabel">01 / DIE APP</span><h2>Deine Sammlung.<br/>Dein Überblick.</h2><p>Karten erfassen, Varianten verwalten und Sets vervollständigen – im Browser und auf Android.</p><Link href="/collection" className="tcgButton">Web-App entdecken ↗</Link></div>
          <div className="v3Dashboard" aria-label="Vorschau der Cardyssey-Sammlungsfunktionen"><div className="v3DashTop"><strong>Cardyssey</strong><span>COLLECTION</span></div><div className="v3DashHeading"><strong>Meine Karten</strong><span>Sets · Sammlung · Preise</span></div><div className="v3DashCards">{cards.map(c=><div key={c.src}><img src={c.src} alt={c.name}/></div>)}</div><div className="v3DashBottom">DEINE KARTEN. DEIN FORTSCHRITT.</div></div>
        </article>
        <article className="v3Path v3PathStore" id="shop"><div className="v3PathCopy"><span className="tcgMiniLabel">02 / DER SHOP</span><h2>Für deinen<br/>nächsten Fund.</h2><p>Entdecke unseren Cardyssey-Shop rund um Pokémon-TCG und Sammelzubehör.</p><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Shop besuchen ↗</a></div>
          <div className="v3ShopVisual"><span>THE CARDYSSEY SHOP</span><div className="v3ShopCard"><img src="/landing/cards/swsh12pt5-160.png" alt="Pokémon-Sammelkarte als TCG-Produktbeispiel"/></div><strong>ENTDECKEN.<br/>SAMMELN.<br/>WEITERGEHEN.</strong></div>
        </article>
      </section>
      <section className="tcgWrap v3Features" id="funktionen"><div className="v3SectionTitle"><span className="tcgMiniLabel">ALLES, WAS DU BRAUCHST</span><h2>Weniger verwalten.<br/><em>Mehr sammeln.</em></h2></div>
        <div className="v3FeaturesRow"><Link href="/scan"><span>01 / SCANNER</span><h3>Karte scannen.</h3><p>Erkennen, prüfen, hinzufügen.</p><b>↗</b></Link><Link href="/collection"><span>02 / SAMMLUNG</span><h3>Alles an einem Ort.</h3><p>Karten, Sets und Varianten.</p><b>↗</b></Link><Link href="/collection"><span>03 / PREISE</span><h3>Werte im Blick.</h3><p>Verfügbare Preise und Entwicklungen.</p><b>↗</b></Link><Link href="/friends"><span>04 / COMMUNITY</span><h3>Zusammen sammeln.</h3><p>Freunde und Karten teilen.</p><b>↗</b></Link></div>
      </section>
      <section className="v3Community" id="community"><div className="tcgWrap v3CommunityInner"><div><span className="tcgMiniLabel">GEMEINSAM STATT ALLEIN</span><h2>Eine Leidenschaft.<br/><em>Viele Sammler.</em></h2><p>Teile Lieblingskarten, entdecke die Sammlungen deiner Freunde und tauscht euch direkt in Cardyssey aus.</p><Link href="/register" className="tcgButton tcgButtonLine">Community entdecken ↗</Link></div><div className="v3CommunityCards"><img src="/landing/cards/sv4-234.png" alt="Pokémon-Sammelkarte"/><img src="/landing/cards/sv3-223.png" alt="Pokémon-Sammelkarte"/></div></div></section>
      <section className="tcgWrap v3Bottom"><div><span className="tcgMiniLabel">CARDYSSEY</span><h2>Dein nächster Schritt<br/>im Hobby.</h2></div><div className="v3BottomButtons"><Link href="/register" className="tcgButton">Kostenlos starten ↗</Link><a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">Zum Shop ↗</a><a href={ANDROID_APK_DOWNLOAD_URL} className="v3Apk">Android-App herunterladen →</a></div></section>
    </main>
    <footer className="tcgFooter"><div className="tcgWrap tcgFooterInner"><Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link><span>© 2026 Cardyssey</span><nav><a href="https://shop.cardyssey.de">Shop</a><Link href="/impressum">Impressum</Link><Link href="/datenschutz">Datenschutz</Link><Link href="/login">Login</Link></nav></div></footer>
  </div>;
}
