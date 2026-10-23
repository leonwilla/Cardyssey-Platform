import Link from 'next/link'
import Image from 'next/image'
import '../redesign.css'
import { SiteHeader } from '@/components/site-header'
import { SiteFooter } from '@/components/site-footer'
const groups = [
 { name: 'Einzelkarten', about: 'Pokémon-Karten und weitere TCG-Einzelkarten.', href:'/shop?design=preview' },
 { name: 'Booster & Displays', about: 'Originalversiegelte Booster, Displays und Boxen.', href:'/shop?design=preview' },
 { name: 'Figuren & Plüsch', about: 'Sammlerfiguren und Plüschartikel.', href:'/shop?design=preview' },
 { name: 'Zubehör', about: 'Hüllen, Toploader und Aufbewahrung.', href:'/shop?design=preview' },
]
export default function ShopDesignPreview(){return <div className="cardysseyRedesign" style={{minHeight:'100vh'}}>
 <SiteHeader/>
 <div className="mx-auto max-w-7xl px-5 pt-5 md:px-8"><Link href="https://shop.cardyssey.de/" className="text-sm font-medium underline underline-offset-4">← Zum bisherigen Shop</Link></div>
 <main className="mx-auto max-w-7xl px-5 py-12 md:px-8 md:py-20">
  <span className="text-sm font-semibold uppercase tracking-widest text-primary">Shop · Designvorschau</span>
  <div className="mt-5 grid items-center gap-8 md:grid-cols-2 md:gap-14">
   <div><h1 className="font-serif text-5xl leading-tight md:text-7xl">Alles für deine <em className="text-primary">Sammlung.</em></h1><p className="mt-6 text-lg text-muted-foreground">Entdecke Einzelkarten, versiegelte Produkte und Zubehör. Diese Seite ist ein Designentwurf – keine separate Bestellabwicklung.</p>
    <Link href="/shop?design=preview" className="mt-8 inline-flex rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground">Aktuelles Sortiment ansehen →</Link>
   </div>
   <div className="relative aspect-[4/3] overflow-hidden rounded-3xl bg-paper-deep"><Image src="/landing/cards/base1-4.png" alt="Pokémon-Sammelkarte als Beispiel für das Sortiment" fill className="object-contain p-8" sizes="(min-width:768px) 45vw,90vw"/></div>
  </div>
  <h2 className="mb-6 mt-20 font-serif text-4xl">Kategorien</h2>
  <div className="grid gap-4 sm:grid-cols-2">{groups.map(group=><Link key={group.name} href={group.href} className="rounded-2xl border border-border bg-background p-7 transition-colors hover:border-primary"><h3 className="font-serif text-2xl">{group.name} ↗</h3><p className="mt-3 text-muted-foreground">{group.about}</p></Link>)}</div>
  <p className="mt-12 text-sm text-muted-foreground">Nur Vorschau: Katalog, Warenkorb, Bezahlung und Bestellungen bleiben im bestehenden Shop. Es werden keine Produkte oder Preise erfunden.</p>
 </main><SiteFooter/></div>}
