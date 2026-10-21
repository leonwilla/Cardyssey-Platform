import { ArrowDownRight } from 'lucide-react'
import { CardFan } from '@/components/card-fan'

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-7xl items-center gap-8 px-5 pb-12 pt-10 sm:gap-12 sm:pb-16 md:px-8 md:pt-14 lg:min-h-[calc(100svh-4rem)] lg:grid-cols-12 lg:gap-8 lg:pb-20 lg:pt-6">
        <div className="lg:col-span-5">
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden />
            Die Plattform für Sammelkarten
          </p>
          <h1 className="mt-6 text-balance font-serif text-[clamp(2.75rem,6vw,5.5rem)] leading-[0.95] tracking-[-0.02em]">
            Deine Karten verdienen ein <em className="text-primary">Zuhause.</em>
          </h1>
          <p className="mt-6 max-w-md text-pretty text-lg leading-relaxed text-foreground/75">
            Scannen, ordnen, verstehen, teilen. CARDYSSEY ist der Ort, an dem deine Sammlung lebt
            – und an dem sie weiterwächst.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-x-8 gap-y-4">
            <a
              href="/register"
              className="rounded-full bg-primary px-7 py-3.5 text-base font-medium text-primary-foreground transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-[0_12px_24px_-12px_rgba(224,82,44,0.7)] motion-reduce:hover:translate-y-0"
            >
              Sammlung anlegen
            </a>
            <a
              href="#reise"
              className="group inline-flex items-center gap-2 text-base font-medium underline decoration-foreground/30 underline-offset-[6px] hover:decoration-foreground"
            >
              So funktioniert&apos;s
              <ArrowDownRight
                className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:translate-y-0.5"
                aria-hidden
              />
            </a>
          </div>
        </div>

        <div className="lg:col-span-7">
          <CardFan />
        </div>
      </div>

      <div className="border-y border-border/70 bg-paper-deep/50">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-8 gap-y-2 px-5 py-4 text-sm text-muted-foreground md:px-8">
          <p>
            <span className="font-medium text-foreground">Jetzt für Pokémon-Sammlungen.</span>{' '}
            Weitere Sammelkartenspiele sind geplant.
          </p>
          <p className="font-serif text-base italic">Scanner · Sammlung · Marktpreise · Wunschliste · Community · Shop</p>
        </div>
      </div>
    </section>
  )
}
