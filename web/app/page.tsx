import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { ANDROID_APK_DOWNLOAD_URL } from "@/lib/android-release";
import "./landing-editorial.css";

const highlights = [
  { number: "01", title: "Sammlung", text: "Karten und Varianten erfassen. Sets sortieren. Deinen Fortschritt sehen.", href: "/collection", action: "Sammlung öffnen" },
  { number: "02", title: "Scanner", text: "Karte vor die Kamera halten, Ergebnis prüfen und direkt hinzufügen.", href: "/scan", action: "Scanner ansehen" },
  { number: "03", title: "Marktpreise", text: "Verfügbare Kartenpreise und Entwicklungen übersichtlich verfolgen.", href: "/collection", action: "Preise entdecken" },
  { number: "04", title: "Community", text: "Mit Freunden sammeln, Karten teilen und miteinander schreiben.", href: "/friends", action: "Community ansehen" },
];

export default function Home() {
  return (
    <div className="tcgHome">
      <header className="tcgHeader">
        <div className="tcgWrap tcgHeaderInner">
          <Link href="/" className="tcgBrand" aria-label="Cardyssey Startseite"><BrandMark /><span>Cardyssey</span></Link>
          <nav aria-label="Hauptnavigation" className="tcgNav">
            <a href="#plattform">Plattform</a><a href="#funktionen">Funktionen</a><a href="#shop">Shop</a><a href="#community">Community</a>
          </nav>
          <div className="tcgHeaderActions"><Link href="/login" className="tcgLogin">Anmelden</Link><Link href="/register" className="tcgButton tcgButtonSmall">Kostenlos starten <span aria-hidden="true">↗</span></Link></div>
        </div>
      </header>

      <main>
        <section className="tcgHero" id="plattform">
          <div className="tcgWrap tcgHeroGrid">
            <div className="tcgHeroCopy">
              <span className="tcgOverline"><span className="tcgDot" /> DIE PLATTFORM FÜR DEINE KARTEN</span>
              <h1>Deine Karten.<br/><span>Deine Welt.</span></h1>
              <p>Scannen, sammeln, Preise verfolgen und neue Karten entdecken. Cardyssey bringt deine Sammlung, die Community und den TCG-Shop zusammen.</p>
              <div className="tcgHeroButtons">
                <Link href="/register" className="tcgButton">Sammlung starten <span aria-hidden="true">↗</span></Link>
                <a href="https://shop.cardyssey.de" className="tcgButton tcgButtonLine">TCG-Shop besuchen <span aria-hidden="true">↗</span></a>
              </div>
              <div className="tcgHeroFacts"><span>WEB & ANDROID</span><span>•</span><span>SAMMLUNG & PREISE</span><span>•</span><span>SHOP & COMMUNITY</span></div>
            </div>
            <div className="tcgHeroStage">
              <div className="tcgStageLabel">COLLECT / TRACK / DISCOVER <span>001—004</span></div>
              <div className="tcgStagePanel">
                <div className="tcgStageSide"><span>YOUR COLLECTION</span><strong>C.</strong><span>POKÉMON TCG</span></div>
                <div className="tcgStageCard tcgCardOne"><span>01 / COLLECTION</span><div className="tcgCardArt"><span>◈</span></div><strong>Every card<br/>has a story.</strong><small>BUILD YOUR COLLECTION</small></div>
                <div className="tcgStageCard tcgCardTwo"><span>02 / DISCOVER</span><div className="tcgCardArt"><span>✦</span></div><strong>Find your<br/>next favorite.</strong><small>EXPLORE THE HOBBY</small></div>
              </div>
              <div className="tcgStageBottom"><span>APP / COMMUNITY / STORE</span><span>MADE FOR COLLECTORS</span></div>
            </div>
          </div>
        </section>

        <section className="tcgChoices tcgWrap" aria-label="Cardyssey entdecken">
          <Link className="tcgChoice tcgChoiceApp" href="/collection">
            <span className="tcgChoiceTop">01 — DIE PLATTFORM <span>↗</span></span>
            <div><span className="tcgMiniLabel">CARDYSSEY APP</span><h2>Alles im Blick.<br/>Jede Karte zählt.</h2><p>Deine Sammlung, dein Scanner, deine Preise. Ein Platz für alles, was du sammelst.</p><span className="tcgChoiceLink">Zur Web-App <span aria-hidden="true">↗</span></span></div>
            <div className="tcgChoiceDecor tcgAppDecor" aria-hidden="true"><span>COLLECTION</span><strong>MY CARDS</strong><i/><i/><i/></div>
          </Link>
          <a className="tcgChoice tcgChoiceShop" href="https://shop.cardyssey.de" id="shop">
            <span className="tcgChoiceTop">02 — DER TCG-SHOP <span>↗</span></span>
            <div><span className="tcgMiniLabel">CARDYSSEY SHOP</span><h2>Neues entdecken.<br/>Weiter sammeln.</h2><p>Der eigene Cardyssey-Shop für Pokémon-TCG-Produkte und Sammelzubehör.</p><span className="tcgChoiceLink">Zum Shop <span aria-hidden="true">↗</span></span></div>
            <div className="tcgChoiceDecor tcgShopDecor" aria-hidden="true"><span>THE COLLECTOR’S CORNER</span><strong>TCG / STORE</strong><b>✦</b></div>
          </a>
        </section>

        <section className="tcgFeatures tcgWrap" id="funktionen">
          <div className="tcgSectionHead"><div><span className="tcgMiniLabel">DIE FUNKTIONEN</span><h2>Für das, was Sammeln<br/><em>wirklich ausmacht.</em></h2></div><p>Kein Tabellenchaos. Keine umständlichen Umwege. Nur die Funktionen, die du für deine Karten brauchst.</p></div>
          <div className="tcgFeatureGrid">{highlights.map((feature) => (
            <Link href={feature.href} className="tcgFeature" key={feature.number}>
              <span className="tcgFeatureNum">{feature.number} / CARDYSSEY <span>↗</span></span>
              <div className="tcgFeatureGlyph" aria-hidden="true">{feature.number === "01" ? "▧" : feature.number === "02" ? "⌗" : feature.number === "03" ? "↗" : "◎"}</div>
              <h3>{feature.title}</h3><p>{feature.text}</p><span className="tcgFeatureAction">{feature.action} →</span>
            </Link>
          ))}</div>
        </section>

        <section className="tcgCommunity" id="community"><div className="tcgWrap tcgCommunityInner">
          <div><span className="tcgMiniLabel">MEHR ALS EINE SAMMLUNG</span><h2>Das Hobby verbindet.<br/><em>Cardyssey auch.</em></h2><p>Zeig deine Karten, entdecke andere Sammlungen und bleib mit Freunden in Kontakt. Zusammen macht Sammeln einfach mehr Spaß.</p><Link href="/register" className="tcgButton tcgButtonLine">Community entdecken ↗</Link></div>
          <div className="tcgCommunityVisual" aria-hidden="true"><span className="tcgCommunityVisualTop">CARDYSSEY / COMMUNITY</span><div className="tcgCommunityLines"><span>FRIENDS</span><strong>Collect<br/>together.</strong><span>SHARE / CHAT / DISCOVER</span></div><div className="tcgCommunityCircles"><i/><i/><i/></div></div>
        </div></section>

        <section className="tcgFinal tcgWrap"><span className="tcgMiniLabel">DEINE SAMMLUNG WARTET SCHON</span><h2>Bereit für deine<br/><em>nächste Karte?</em></h2><div className="tcgFinalActions"><Link href="/register" className="tcgButton">Jetzt kostenlos starten ↗</Link><a href={ANDROID_APK_DOWNLOAD_URL} className="tcgButton tcgButtonLine">Android-App herunterladen ↗</a><a href="https://shop.cardyssey.de" className="tcgTextLink">Zum Shop ↗</a></div></section>
      </main>

      <footer className="tcgFooter"><div className="tcgWrap tcgFooterInner"><Link href="/" className="tcgBrand"><BrandMark/><span>Cardyssey</span></Link><span>© 2026 Cardyssey</span><nav aria-label="Rechtliches"><a href="https://shop.cardyssey.de">Shop</a><Link href="/impressum">Impressum</Link><Link href="/datenschutz">Datenschutz</Link><Link href="/login">Login</Link></nav></div></footer>
    </div>
  );
}
