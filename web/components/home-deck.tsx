'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { BrandMark } from '@/components/BrandMark'
import { Camera, Heart, Layers, ShoppingBag, TrendingUp, Users, type LucideIcon } from 'lucide-react'

/**
 * Startseite im Kartendeck-Look (wie App und Webapp): dunkler Spieltisch,
 * Goldschrift, Holo-Kante, Funktionen als Sammelkarten.
 */

const fan = [
  { src: '/landing/cards/sv3-223.png', alt: 'Sammelkarte aus Obsidianflammen' },
  { src: '/landing/cards/base1-4.png', alt: 'Glurak aus dem Grundset' },
  { src: '/landing/cards/sv4-234.png', alt: 'Sammelkarte aus Paradoxrift' },
  { src: '/landing/cards/swsh12pt5-160.png', alt: 'Sammelkarte aus Zenit der Könige' },
]

const features = [
  {
    no: '001',
    icon: Camera as LucideIcon,
    id: 'scannen',
    title: 'Scannen',
    type: 'Kamera',
    text: 'Karte in den Rahmen halten – Cardyssey erkennt Set, Nummer und Variante. Du prüfst kurz und legst sie ab.',
    points: ['Foto, Screenshot oder Kamera', 'Variante wählen: Normal, Holo, Reverse'],
  },
  {
    no: '002',
    icon: Layers as LucideIcon,
    id: 'sammeln',
    title: 'Sammeln',
    type: 'Ordner',
    text: 'Deine Karten nach Sets, Sprache und Zustand. Fortschritt pro Set, doppelte Karten auf einen Blick.',
    points: ['Alle Sets mit Logo und Fortschritt', 'Deutsch, Englisch und mehr'],
  },
  {
    no: '003',
    icon: TrendingUp as LucideIcon,
    id: 'marktpreise',
    title: 'Preise',
    type: 'Cardmarket',
    text: 'Offizielle Cardmarket-Preise, alle zwei Stunden aktuell. Wertvolle Karten prüfen wir zusätzlich einzeln nach Sprache.',
    points: ['Preisverlauf 7 Tage bis 1 Jahr', 'Wert nach Zustand berechnet'],
  },
  {
    no: '004',
    icon: Heart as LucideIcon,
    id: 'wunschliste',
    title: 'Wunschliste',
    type: 'Jagd',
    text: 'Halte fest, was dir noch fehlt. Sets zeigen fehlende Karten, die Wunschliste merkt sich deine Ziele.',
    points: ['Fehlkarten pro Set', 'Abgleich mit dem Shop'],
  },
  {
    no: '005',
    icon: Users as LucideIcon,
    id: 'community',
    title: 'Community',
    type: 'Freunde',
    text: 'Freunde hinzufügen, Sammlungen ansehen, Karten im Chat teilen und tauschen.',
    points: ['Freundescode und Chat', 'Vitrine mit deinen Lieblingskarten'],
  },
  {
    no: '006',
    icon: ShoppingBag as LucideIcon,
    id: 'shop',
    title: 'Shop',
    type: 'Handel',
    text: 'Einzelkarten, Booster und Zubehör im Cardyssey-Shop – passend zu deiner Wunschliste.',
    points: ['Einzelkarten nach Set', 'Booster, Displays, Zubehör'],
  },
]

const steps = [
  ['Scannen', 'Karte vor die Kamera halten oder ein Foto hochladen.'],
  ['Prüfen', 'Set, Nummer und Variante bestätigen – fertig.'],
  ['Verfolgen', 'Wert, Preisverlauf und Set-Fortschritt wachsen mit.'],
]

function HomeHeader() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    fetch('/api/auth/me', { cache: 'no-store' })
      .then((r) => setLoggedIn(r.ok))
      .catch(() => {})
  }, [])
  return (
    <header className="hd-header">
      <div className="hd-wrap hd-headerRow">
        <Link href="/" className="hd-brand" aria-label="Cardyssey Startseite">
          <BrandMark />
          <span>Cardyssey</span>
        </Link>
        <nav className={open ? 'hd-nav open' : 'hd-nav'} aria-label="Hauptnavigation">
          <a href="#funktionen" onClick={() => setOpen(false)}>Funktionen</a>
          <a href="#so-gehts" onClick={() => setOpen(false)}>So geht&apos;s</a>
          <a href="#app" onClick={() => setOpen(false)}>App</a>
          <a href="https://shop.cardyssey.de" onClick={() => setOpen(false)}>Shop</a>
        </nav>
        <div className="hd-headerActions">
          {loggedIn ? (
            <Link href="/collection" className="hd-btn hd-btnGold hd-btnSmall">Zur Sammlung</Link>
          ) : (
            <Link href="/login" className="hd-btn hd-btnGold hd-btnSmall">Anmelden</Link>
          )}
          <button
            type="button"
            className="hd-menu"
            aria-expanded={open}
            aria-label={open ? 'Menü schließen' : 'Menü öffnen'}
            onClick={() => setOpen((v) => !v)}
          >
            <span /><span /><span />
          </button>
        </div>
      </div>
    </header>
  )
}

function CardFan() {
  const [active, setActive] = useState(1)
  return (
    <div className="hd-fan" role="group" aria-label="Kartenfächer">
      {fan.map((card, i) => {
        const offset = i - active
        return (
          <button
            key={card.src}
            type="button"
            className={i === active ? 'hd-fanCard active' : 'hd-fanCard'}
            style={{
              transform: `translateX(calc(-50% + ${offset * 62}px)) translateY(${Math.abs(offset) * 16}px) rotate(${offset * 8}deg)`,
              zIndex: 10 - Math.abs(offset),
            }}
            onClick={() => setActive(i)}
            aria-label={card.alt}
            aria-pressed={i === active}
          >
            <img src={card.src} alt="" />
          </button>
        )
      })}
    </div>
  )
}

export function HomeDeck() {
  return (
    <div className="hd">
      <HomeHeader />
      <main>
        <section className="hd-hero">
          <div className="hd-wrap hd-heroGrid">
            <div>
              <span className="hd-eyebrow">Pokémon-Sammelkarten · Scanner · Preise</span>
              <h1 className="hd-title">
                Deine Sammlung.<br />
                <span className="hd-gold">Dein Deck.</span>
              </h1>
              <p className="hd-lead">
                Scanne deine Karten, sieh ihren Wert mit echten Cardmarket-Preisen und behalte jedes Set im Blick –
                im Browser und in der App.
              </p>
              <div className="hd-ctaRow">
                <Link href="/collection" className="hd-btn hd-btnGold">Zur Sammlung</Link>
                <a href="#funktionen" className="hd-btn hd-btnGhost">Was Cardyssey kann</a>
              </div>
              <dl className="hd-stats">
                <div><dt>Preise</dt><dd>alle 2 h</dd></div>
                <div><dt>Sets</dt><dd>alle seit 1999</dd></div>
                <div><dt>Sprachen</dt><dd>DE · EN +</dd></div>
              </dl>
            </div>
            <CardFan />
          </div>
        </section>

        <section id="funktionen" className="hd-section">
          <div className="hd-wrap">
            <span className="hd-eyebrow hd-eyebrowDark">Funktionen</span>
            <h2 className="hd-h2">Sechs Karten für dein Hobby</h2>
            <p className="hd-sub">Alles, was eine Sammlung braucht – in einem Deck.</p>
            <div className="hd-cards">
              {features.map((f) => (
                <article key={f.id} id={f.id} className="hd-card">
                  <header>
                    <strong>{f.title}</strong>
                    <span>{f.type}</span>
                  </header>
                  <div className="hd-cardArt" aria-hidden>
                    <f.icon strokeWidth={1.6} />
                    <span>{f.no}</span>
                  </div>
                  <p>{f.text}</p>
                  <ul>
                    {f.points.map((p) => <li key={p}>{p}</li>)}
                  </ul>
                  <footer>
                    <span>{f.no}/006</span>
                    <span>Cardyssey</span>
                  </footer>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="so-gehts" className="hd-section hd-sectionTable">
          <div className="hd-wrap">
            <span className="hd-eyebrow">So geht&apos;s</span>
            <h2 className="hd-h2 hd-onTable">In drei Zügen zur Sammlung</h2>
            <ol className="hd-steps">
              {steps.map(([title, text], i) => (
                <li key={title}>
                  <span className="hd-stepNo">{i + 1}</span>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="app" className="hd-section">
          <div className="hd-wrap hd-appGrid">
            <div>
              <span className="hd-eyebrow hd-eyebrowDark">App &amp; Web</span>
              <h2 className="hd-h2">Ein Konto. Überall dieselbe Sammlung.</h2>
              <p className="hd-sub">
                Die Android-App scannt mit der Kamera, die Webapp zeigt dir alles groß am Bildschirm. Beide sehen gleich
                aus und bleiben automatisch synchron.
              </p>
              <ul className="hd-checks">
                <li>Scanner mit Rahmen, Licht und Helligkeit</li>
                <li>Sammlungswert in Cardmarket- oder eBay-Preisen</li>
                <li>Preisverlauf für jede Karte</li>
                <li>Hell, Dunkel und mehrere Farbthemen</li>
              </ul>
            </div>
            <div className="hd-phone" aria-hidden>
              <div className="hd-phoneScreen">
                <div className="hd-phoneHero">
                  <span className="hd-eyebrow">Deine Sammlung</span>
                  <strong className="hd-gold">1.284,50 €</strong>
                  <small>Cardmarket · nach Zustand bewertet</small>
                  <div className="hd-phoneStats"><span>412 Karten</span><span>23 Sets</span></div>
                </div>
                <div className="hd-phoneGrid">
                  {fan.map((c) => <img key={c.src} src={c.src} alt="" />)}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="hd-section">
          <div className="hd-wrap">
            <div className="hd-closing">
              <span className="hd-eyebrow">Bereit?</span>
              <h2 className="hd-h2 hd-onTable">Deine Odyssee beginnt mit einer Karte.</h2>
              <p>Leg deine Sammlung an, scanne die ersten Karten und sieh, was sie wert sind.</p>
              <div className="hd-ctaRow hd-center">
                <Link href="/collection" className="hd-btn hd-btnGold">Sammlung öffnen</Link>
                <a href="https://shop.cardyssey.de" className="hd-btn hd-btnGhost">Zum Shop</a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <footer className="hd-footer">
        <div className="hd-wrap hd-footerGrid">
          <div>
            <div className="hd-brand"><BrandMark /><span>Cardyssey</span></div>
            <p>Ein Zuhause für deine Sammelkarten.</p>
          </div>
          <nav aria-label="Plattform">
            <strong>Plattform</strong>
            <Link href="/collection">Sammlung</Link>
            <Link href="/scan">Scanner</Link>
            <Link href="/sets">Sets</Link>
            <Link href="/marketplace">Markt</Link>
          </nav>
          <nav aria-label="Rechtliches">
            <strong>Rechtliches</strong>
            <Link href="/impressum">Impressum</Link>
            <Link href="/datenschutz">Datenschutz</Link>
          </nav>
        </div>
        <p className="hd-wrap hd-legal">
          © {new Date().getFullYear()} Cardyssey. Pokémon ist eine Marke von Nintendo, Creatures Inc. und GAME FREAK inc.
          Cardyssey steht in keiner offiziellen Verbindung zu diesen Unternehmen.
        </p>
      </footer>
    </div>
  )
}
