import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import {
  ANDROID_APK_DOWNLOAD_URL,
  formatAndroidReleaseDate,
  getLatestAndroidRelease,
} from "@/lib/android-release";
import "./landing-editorial.css";

const capabilities = [
  {
    index: "01 / SAMMLUNG",
    title: "Eine Sammlung, die mitdenkt.",
    text: "Karten, Varianten, Mengen und Sammlungswerte übersichtlich an einem Ort. Ohne komplizierte Listen.",
  },
  {
    index: "02 / SCANNER",
    title: "Weniger suchen. Mehr sammeln.",
    text: "Karten mit dem Scanner erfassen, passende Einträge prüfen und direkt in deine Sammlung übernehmen.",
  },
  {
    index: "03 / PREISE",
    title: "Werte besser einordnen.",
    text: "Verfügbare Marktpreise und Preisentwicklungen direkt neben deinen Karten ansehen.",
  },
];

export default async function Home() {
  const androidRelease = await getLatestAndroidRelease();

  return (
    <div className="editorialHome">
      <header className="ehHeader">
        <div className="ehHeaderInner">
          <Link href="/" className="ehBrand" aria-label="Cardyssey Startseite">
            <BrandMark />
            <span>Cardyssey</span>
          </Link>
          <nav className="ehNav" aria-label="Hauptnavigation">
            <a href="#funktionen">Funktionen</a>
            <a href="#ablauf">So funktioniert&apos;s</a>
            <a href="#community">Community</a>
            <a href="https://shop.cardyssey.de">Shop</a>
          </nav>
          <div className="ehHeaderActions">
            <Link href="/login">Anmelden</Link>
            <Link href="/register" className="ehButton ehButtonSmall">Kostenlos starten</Link>
          </div>
        </div>
      </header>

      <main>
        <div className="ehContainer">
          <section className="ehHero" aria-labelledby="ehTitle">
            <div>
              <span className="ehKicker">Dein Platz für Pokémon-Karten</span>
              <h1 id="ehTitle">Sammeln ist persönlich. <em>Dein Überblick auch.</em></h1>
              <p className="ehLead">
                Organisiere deine Karten, entdecke Sets und behalte deine Sammlung im Blick.
                Cardyssey bringt alles zusammen, was das Sammeln einfacher macht.
              </p>
              <div className="ehActions">
                <Link href="/register" className="ehButton">Sammlung starten <span aria-hidden="true">↗</span></Link>
                <Link href="/collection" className="ehButton ehButtonOutline">Web-App öffnen</Link>
              </div>
              <p className="ehUnderNote">Kostenloser Einstieg · Im Browser und auf Android nutzbar</p>
            </div>

            <div className="ehVisual" aria-label="Beispielhafte Darstellung der Sammlungsübersicht">
              <div className="ehPreview">
                <div className="ehPreviewTop">
                  <strong>Cardyssey / Sammlung</strong>
                  <span>Übersicht</span>
                </div>
                <div className="ehPreviewBody">
                  <div className="ehPreviewCaption">
                    <strong>Meine Sammlung</strong>
                    <span>Beispielansicht</span>
                  </div>
                  <div className="ehPreviewTiles">
                    <div className="ehPreviewTile"><small>Karten</small><strong>Sammlung</strong></div>
                    <div className="ehPreviewTile"><small>Organisieren</small><strong>Sets</strong></div>
                    <div className="ehPreviewTile"><small>Im Blick</small><strong>Werte</strong></div>
                  </div>
                  <div className="ehPreviewCaption"><strong>Deine Karten</strong><span>Nach Set sortiert</span></div>
                  <div className="ehPreviewList">
                    <div className="ehPreviewRow"><div className="ehPreviewThumb" /><div><strong>Set entdecken</strong><span>Karten &amp; Varianten</span></div><strong>↗</strong></div>
                    <div className="ehPreviewRow"><div className="ehPreviewThumb" /><div><strong>Sammlung pflegen</strong><span>Mengen &amp; Fortschritt</span></div><strong>↗</strong></div>
                    <div className="ehPreviewRow"><div className="ehPreviewThumb" /><div><strong>Wunschliste ansehen</strong><span>Fehlende Karten</span></div><strong>↗</strong></div>
                  </div>
                </div>
              </div>
              <div className="ehAside">Alles an einem Ort. <strong>Ohne Tabellenchaos.</strong></div>
            </div>
          </section>
        </div>

        <div className="ehRibbon">
          <div className="ehContainer ehRibbonInner">
            <strong>Für Sammler gemacht.</strong>
            <span>Kartenscanner</span>
            <span>Set-Übersichten</span>
            <span>Preisverläufe</span>
            <span>Freunde &amp; Community</span>
          </div>
        </div>

        <section className="ehContainer ehSection" id="funktionen" aria-labelledby="ehFeaturesTitle">
          <div className="ehSectionIntro">
            <span className="ehKicker">Das Wesentliche, gut gelöst</span>
            <h2 id="ehFeaturesTitle">Mehr Zeit für deine Karten. Weniger für die Verwaltung.</h2>
            <p>Vom ersten Scan bis zum nächsten vollständigen Set: Deine Sammlung bleibt übersichtlich, auch wenn sie wächst.</p>
          </div>
          <div className="ehFeatures">
            {capabilities.map((item) => (
              <article className="ehFeature" key={item.index}>
                <span className="ehFeatureIndex">{item.index}</span>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="ehSplitBand" id="ablauf">
          <section className="ehContainer ehSplit" aria-labelledby="ehHowTitle">
            <div className="ehSplitCopy">
              <span className="ehKicker">Einfach loslegen</span>
              <h2 id="ehHowTitle">Deine Karten. Dein Tempo.</h2>
              <p>
                Du musst keine neue Art zu sammeln lernen. Karten finden, hinzufügen
                und nach Sets sortieren – Cardyssey hält die wichtigen Informationen zusammen.
              </p>
              <Link href="/register" className="ehButton">Jetzt ausprobieren <span aria-hidden="true">↗</span></Link>
            </div>
            <div className="ehProcess">
              <div className="ehProcessItem"><span className="ehProcessNumber">01</span><div><strong>Karten finden</strong><p>Per Scanner oder Suche nach deinen Karten schauen.</p></div></div>
              <div className="ehProcessItem"><span className="ehProcessNumber">02</span><div><strong>Zur Sammlung hinzufügen</strong><p>Variante und Menge auswählen und sicher festhalten.</p></div></div>
              <div className="ehProcessItem"><span className="ehProcessNumber">03</span><div><strong>Den Überblick behalten</strong><p>Sets, Wunschliste und verfügbare Preisinfos an einem Ort verwalten.</p></div></div>
            </div>
          </section>
        </div>

        <section className="ehContainer ehSplit" id="community" aria-labelledby="ehCommunityTitle">
          <div className="ehProcess">
            <div className="ehProcessItem"><span className="ehProcessNumber">01</span><div><strong>Freunde hinzufügen</strong><p>Mit anderen Sammlern in Verbindung bleiben.</p></div></div>
            <div className="ehProcessItem"><span className="ehProcessNumber">02</span><div><strong>Karten teilen</strong><p>Deine Sammlung und Wunschliste gemeinsam entdecken.</p></div></div>
            <div className="ehProcessItem"><span className="ehProcessNumber">03</span><div><strong>Gemeinsam sammeln</strong><p>Austauschen, chatten und neue Karten entdecken.</p></div></div>
          </div>
          <div className="ehSplitCopy">
            <span className="ehKicker">Gemeinsam macht es mehr Spaß</span>
            <h2 id="ehCommunityTitle">Deine Sammlung ist erst der Anfang.</h2>
            <p>Bleib mit Freunden in Kontakt, zeig deine Lieblingskarten und entdecke, was andere Sammler begeistert.</p>
            <Link href="/register" className="ehButton ehButtonOutline">Community entdecken <span aria-hidden="true">↗</span></Link>
          </div>
        </section>

        <div className="ehContainer">
          <div className="ehShop">
            <div>
              <strong>Auch unterwegs dabei.</strong>
              <p>Nutze Cardyssey im Browser oder lade die Android-App herunter.
                {androidRelease ? ` Android-Version vom ${formatAndroidReleaseDate(androidRelease.builtAt)}.` : ""}
              </p>
            </div>
            <a href={ANDROID_APK_DOWNLOAD_URL} className="ehTextLink">Android herunterladen ↗</a>
          </div>
          <div className="ehShop">
            <div>
              <strong>Auf der Suche nach TCG-Produkten?</strong>
              <p>Unser eigenständiger Shop ist unter shop.cardyssey.de erreichbar.</p>
            </div>
            <a href="https://shop.cardyssey.de" className="ehTextLink">Zum Shop ↗</a>
          </div>
          <section className="ehLast" aria-labelledby="ehLastTitle">
            <span className="ehKicker">Bereit für mehr Überblick?</span>
            <h2 id="ehLastTitle">Mach deine Sammlung zu deiner Cardyssey.</h2>
            <p>Ein Platz für deine Karten, Sets und alles, was du noch sammeln möchtest.</p>
            <Link href="/register" className="ehButton">Kostenlos starten <span aria-hidden="true">↗</span></Link>
          </section>
          <footer className="ehFooter">
            <Link href="/" className="ehBrand"><BrandMark /><span>Cardyssey</span></Link>
            <span>© 2026 Cardyssey</span>
            <div className="ehFooterLinks">
              <a href="https://shop.cardyssey.de">Shop</a>
              <Link href="/impressum">Impressum</Link>
              <Link href="/datenschutz">Datenschutz</Link>
              <Link href="/login">Anmelden</Link>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
}
