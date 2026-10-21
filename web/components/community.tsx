import { ArrowRight } from 'lucide-react'
import Image from 'next/image'
import { media } from '@/lib/media'

export function Community() {
  return (
    <section id="community" aria-labelledby="community-title" className="scroll-mt-16 px-3 md:px-5">
      <div className="relative mx-auto flex min-h-[620px] max-w-[1600px] flex-col justify-end overflow-hidden rounded-[2rem] md:min-h-[740px] md:rounded-[2.5rem]">
        <Image src={media.community.src} alt={media.community.alt} fill sizes="100vw" className="object-cover" />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-foreground/90 via-foreground/45 via-45% to-transparent"
        />
        <div
          aria-hidden
          className="absolute inset-0 hidden bg-gradient-to-r from-foreground/40 to-transparent md:block"
        />

        <div className="relative p-6 text-background sm:p-10 md:p-14">
          <div className="max-w-3xl">
            <p className="text-sm text-background/80">Community</p>
            <h2
              id="community-title"
              className="mt-3 text-balance font-serif text-5xl leading-[0.98] tracking-tight [text-shadow:0_2px_24px_rgba(29,41,36,0.35)] md:text-7xl"
            >
              Sammeln ist schöner, wenn man es <em>teilen</em> kann.
            </h2>
            <p className="mt-6 max-w-lg text-pretty text-lg leading-relaxed text-background/90">
              Zeig deine Lieblingsstücke, entdecke andere Sammlungen und komm mit Menschen ins
              Gespräch, die genauso für Karten brennen wie du.
            </p>
            <a
              href="/register"
              className="group mt-8 inline-flex items-center gap-2 rounded-full border border-background/50 bg-background/10 px-6 py-3 font-medium text-background backdrop-blur-sm transition-colors hover:bg-background hover:text-foreground"
            >
              Die Community kennenlernen
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
