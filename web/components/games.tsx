import { NotifyForm } from '@/components/notify-form'

export function Games() {
  return (
    <section id="spiele" className="scroll-mt-16 bg-foreground py-24 text-background md:py-36">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <p className="text-sm text-background/60">Unterstützte Spiele</p>

        <div className="mt-10 border-t border-background/20">
          <div className="flex flex-col gap-4 border-b border-background/20 py-8 md:flex-row md:items-end md:justify-between">
            <p className="font-serif text-7xl leading-none tracking-tight md:text-[9rem]">Pokémon</p>
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              <span className="size-1.5 rounded-full bg-primary-foreground" aria-hidden />
              Jetzt verfügbar
            </span>
          </div>
          <div className="flex flex-col gap-4 border-b border-background/20 py-8 md:flex-row md:items-end md:justify-between">
            <p className="font-serif text-5xl italic leading-none tracking-tight text-background/35 md:text-[6rem]">
              Weitere Spiele
            </p>
            <span className="inline-flex w-fit items-center rounded-full border border-background/30 px-4 py-2 text-sm text-background/70">
              In Planung
            </span>
          </div>
        </div>

        <div className="mt-14 grid gap-8 md:grid-cols-2 md:items-end">
          <p className="max-w-md text-pretty text-lg leading-relaxed text-background/75">
            Wir starten mit Pokémon und bauen CARDYSSEY Schritt für Schritt aus. Sag uns Bescheid,
            wenn du informiert werden möchtest, sobald weitere Sammelkartenspiele dazukommen.
          </p>
          <NotifyForm />
        </div>
      </div>
    </section>
  )
}
