import { TiltCard } from '@/components/tilt-card'
import { cards } from '@/lib/cards'

export function Closing() {
  return (
    <section id="start" className="scroll-mt-16 overflow-hidden py-24 md:py-36">
      <div className="mx-auto flex max-w-7xl flex-col items-center px-5 text-center md:px-8">
        <div className="relative mb-14 flex h-64 w-full max-w-md items-center justify-center md:h-80">
          <div className="absolute left-1/2 w-32 -translate-x-[115%] md:w-44">
            <div className="animate-float-slow" style={{ ['--r' as string]: '-10deg' }}>
              <TiltCard src={cards[0].src} alt="" sizes="180px" />
            </div>
          </div>
          <div className="relative z-10 w-40 md:w-52">
            <div className="animate-float-slow" style={{ animationDelay: '-2s' }}>
              <TiltCard src={cards[2].src} alt="Illustrierte Sammelkarte Ignis Fox" sizes="220px" intensity={18} />
            </div>
          </div>
          <div className="absolute left-1/2 w-32 translate-x-[15%] md:w-44">
            <div className="animate-float-slow" style={{ ['--r' as string]: '10deg', animationDelay: '-4s' }}>
              <TiltCard src={cards[4].src} alt="" sizes="180px" />
            </div>
          </div>
        </div>

        <h2 className="max-w-4xl text-balance font-serif text-5xl leading-[0.95] tracking-tight md:text-8xl">
          Deine Odyssee beginnt mit <em className="text-primary">einer Karte.</em>
        </h2>
        <p className="mt-6 max-w-lg text-pretty text-lg leading-relaxed text-foreground/75">
          Leg deine Sammlung an, scanne deine ersten Karten und finde heraus, wohin die Reise geht.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <a
            href="/register"
            className="rounded-full bg-primary px-7 py-4 font-medium text-primary-foreground transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-[0_12px_24px_-12px_rgba(224,82,44,0.7)] motion-reduce:hover:translate-y-0"
          >
            Sammlung anlegen
          </a>
          <a
            href="#reise"
            className="rounded-full border border-foreground/25 px-7 py-4 font-medium transition-colors hover:border-foreground hover:bg-foreground/5"
          >
            Mehr erfahren
          </a>
        </div>
      </div>
    </section>
  )
}
