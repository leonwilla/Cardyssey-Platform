import { ArrowUpRight } from 'lucide-react'
import Image from 'next/image'
import { media } from '@/lib/media'

/** Category structure for the upcoming catalogue – no products or prices yet. */
const categories = [
  { id: 'einzelkarten', title: 'Einzelkarten', text: 'Karten für deine Sammlung entdecken.' },
  { id: 'displays', title: 'Booster & Displays', text: 'Originalversiegelte Booster, Displays und Boxen.' },
  { id: 'figuren', title: 'Figuren & Plüsch', text: 'Sammlerartikel und Geschenkideen.' },
  { id: 'zubehoer', title: 'Zubehör', text: 'Hüllen, Toploader und Aufbewahrung.' },
]

export function Shop() {
  return (
    <section id="shop" aria-labelledby="shop-title" className="scroll-mt-16 py-24 md:py-32">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 md:px-8 lg:grid-cols-12 lg:gap-16">
        <div className="relative aspect-[4/3] overflow-hidden rounded-[2rem] lg:col-span-6 lg:aspect-auto lg:min-h-[600px]">
          <Image
            src={media.shop.src}
            alt={media.shop.alt}
            fill
            sizes="(min-width: 1024px) 50vw, 100vw"
            className="object-cover"
          />
        </div>

        <div className="flex flex-col justify-center lg:col-span-6">
          <p className="text-sm text-muted-foreground">Der Shop</p>
          <h2
            id="shop-title"
            className="mt-4 text-balance font-serif text-5xl leading-[0.98] tracking-tight md:text-6xl"
          >
            Alles für die nächste Etappe – <em className="text-primary">gleich nebenan.</em>
          </h2>
          <p className="mt-6 max-w-md text-pretty text-lg leading-relaxed text-foreground/75">
            Pokémon, Yu-Gi-Oh! und Dragon Ball: Im CARDYSSEY-Shop entstehen Angebote für Einzelkarten,
            originalversiegelte Produkte und Sammlerzubehör. Das Sortiment befindet sich im Aufbau.
          </p>

          <ul className="mt-10 grid gap-3 sm:grid-cols-2">
            {categories.map((c) => (
              <li key={c.id}>
                <a
                  href="https://shop.cardyssey.de/"
                  className="group flex h-full flex-col justify-between gap-6 rounded-2xl border border-border bg-card/60 p-5 transition-colors hover:border-primary/50 hover:bg-card"
                >
                  <span className="flex items-start justify-between gap-4">
                    <span className="font-serif text-2xl leading-tight transition-colors group-hover:text-primary">
                      {c.title}
                    </span>
                    <ArrowUpRight
                      className="mt-1 size-5 shrink-0 text-foreground/50 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
                      aria-hidden
                    />
                  </span>
                  <span className="text-sm leading-relaxed text-muted-foreground">{c.text}</span>
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-sm text-muted-foreground">Das Sortiment ist im Aufbau.</p>
        </div>
      </div>
    </section>
  )
}
