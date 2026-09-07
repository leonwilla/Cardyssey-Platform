import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";

const features = [
  {
    icon: "◫",
    title: "Deine Sammlung",
    text: "Behalte Karten, Varianten, Mengen und Werte zentral im Blick."
  },
  {
    icon: "⌗",
    title: "Scanner & Suche",
    text: "Karten schneller finden, erfassen und direkt deiner Sammlung zuordnen."
  },
  {
    icon: "▦",
    title: "Sets entdecken",
    text: "Sets durchsuchen, Fortschritt verfolgen und fehlende Karten erkennen."
  },
  {
    icon: "♢",
    title: "Community",
    text: "Freunde hinzufügen, Sammlungen entdecken und deine Wishlist teilen."
  },
  {
    icon: "◈",
    title: "Marketplace",
    text: "Karten anderer Sammler entdecken und passende Angebote finden."
  },
  {
    icon: "◎",
    title: "Angebote",
    text: "Preisangebote senden, empfangen, annehmen oder zurückziehen."
  }
];

export default function Home() {
  return (
    <div className="landingPage">
      <header className="landingHeader">
        <Link href="/" className="landingBrand">
          <BrandMark />
          <span>Cardyssey</span>
        </Link>

        <nav className="landingNav">
          <a href="#features">Features</a>
          <a href="#platform">Plattform</a>
          <a href="https://shop.cardyssey.de">Shop</a>
        </nav>

        <div className="landingHeaderActions">
          <Link href="/login" className="landingLoginButton">
            Anmelden
          </Link>

          <Link href="/register" className="primaryButton landingSmallCta">
            Kostenlos starten
          </Link>
        </div>
      </header>

      <main>
        <section className="landingHero">
          <div className="landingHeroCopy">
            <span className="landingEyebrow">
              Deine TCG-Plattform
            </span>

            <h1>
              Sammeln.
              <br />
              Entdecken.
              <br />
              <span>Cardyssey.</span>
            </h1>

            <p>
              Deine Sammlung, Sets, Wishlist, Freunde,
              Marketplace und Angebote in einer Plattform —
              auf Web und Android.
            </p>

            <div className="landingHeroActions">
              <Link href="/collection" className="primaryButton landingBigCta">
                Cardyssey öffnen
                <span>→</span>
              </Link>

              <a
                href="/downloads/cardyssey-latest.apk"
                className="landingSecondaryButton"
              >
                Android herunterladen
              </a>
            </div>

            <div className="landingTrust">
              <span><b>✓</b> Exakte Kartenvarianten</span>
              <span><b>✓</b> Server-Synchronisierung</span>
              <span><b>✓</b> Sammlung & Community</span>
            </div>
          </div>

          <div className="landingHeroVisual" aria-hidden="true">
            <div className="landingOrbit orbitOne" />
            <div className="landingOrbit orbitTwo" />

            <div className="landingCardStack">
              <div className="landingDemoCard demoBack">
                <div className="demoCardGlow" />
              </div>

              <div className="landingDemoCard demoMiddle">
                <div className="demoCardGlow" />
              </div>

              <div className="landingDemoCard demoFront">
                <div className="demoCardTop">
                  <span>COLLECTION</span>
                  <b>01</b>
                </div>

                <div className="demoCardArt">
                  <div className="demoOrb" />
                </div>

                <div className="demoCardInfo">
                  <strong>Deine Reise.</strong>
                  <span>Eine Plattform.</span>
                </div>
              </div>
            </div>

            <div className="landingFloatingBadge badgeTop">
              <span>◈</span>
              Marketplace
            </div>

            <div className="landingFloatingBadge badgeBottom">
              <span>◎</span>
              Live synchronisiert
            </div>
          </div>
        </section>

        <section className="landingStats">
          <div>
            <strong>1</strong>
            <span>Sammlung</span>
          </div>

          <div>
            <strong>∞</strong>
            <span>Karten & Sets</span>
          </div>

          <div>
            <strong>Web + Android</strong>
            <span>Eine Cardyssey</span>
          </div>

          <div>
            <strong>Community</strong>
            <span>Freunde & Handel</span>
          </div>
        </section>

        <section className="landingSection" id="features">
          <div className="landingSectionHead">
            <span className="landingEyebrow">Alles an einem Ort</span>
            <h2>Mehr als nur eine Kartenliste.</h2>
            <p>
              Cardyssey verbindet deine Sammlung mit den Funktionen,
              die du als Sammler wirklich brauchst.
            </p>
          </div>

          <div className="landingFeatureGrid">
            {features.map((feature) => (
              <article className="landingFeatureCard" key={feature.title}>
                <div className="landingFeatureIcon">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landingPlatformSection" id="platform">
          <div className="landingPlatformCopy">
            <span className="landingEyebrow">Web + Android</span>
            <h2>Deine Sammlung bleibt bei dir.</h2>
            <p>
              Cardyssey synchronisiert deine Daten zentral,
              damit du deine Sammlung auf verschiedenen Geräten
              weiterführen kannst.
            </p>

            <div className="landingPlatformActions">
              <Link href="/register" className="primaryButton landingBigCta">
                Account erstellen
              </Link>

              <a
                href="/downloads/cardyssey-latest.apk"
                className="landingSecondaryButton"
              >
                Android APK
              </a>
            </div>
          </div>

          <div className="landingPlatformMock">
            <div className="platformWindow">
              <div className="platformWindowBar">
                <i />
                <i />
                <i />
                <span>cardyssey.de</span>
              </div>

              <div className="platformMockContent">
                <div className="platformMockSidebar">
                  <div className="platformLogoDot" />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>

                <div className="platformMockMain">
                  <div className="platformMockTitle" />
                  <div className="platformMockStats">
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="platformMockCards">
                    <i />
                    <i />
                    <i />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landingShopSection">
          <div>
            <span className="landingEyebrow">Cardyssey Shop</span>
            <h2>TCG-Produkte separat. Cardyssey bleibt die Plattform.</h2>
            <p>
              Der Shop läuft eigenständig unter shop.cardyssey.de,
              bleibt aber Teil derselben Cardyssey-Welt.
            </p>
          </div>

          <a
            href="https://shop.cardyssey.de"
            className="landingSecondaryButton"
          >
            Zum TCG-Shop →
          </a>
        </section>

        <section className="landingFinalCta">
          <div className="landingFinalGlow" />

          <span className="landingEyebrow">Bereit?</span>
          <h2>Starte deine Cardyssey.</h2>
          <p>
            Sammlung aufbauen, Sets vervollständigen und
            deine Kartenwelt an einem Ort verwalten.
          </p>

          <div className="landingHeroActions centered">
            <Link href="/register" className="primaryButton landingBigCta">
              Kostenlos starten
            </Link>

            <Link href="/login" className="landingSecondaryButton">
              Bereits registriert
            </Link>
          </div>
        </section>
      </main>

      <footer className="landingFooter">
        <Link href="/" className="landingBrand">
          <BrandMark />
          <span>Cardyssey</span>
        </Link>

        <span>© 2026 Cardyssey</span>

        <div>
          <a href="https://shop.cardyssey.de">Shop</a>
          <Link href="/login">Login</Link>
        </div>
      </footer>
    </div>
  );
}
