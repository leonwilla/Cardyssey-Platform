import { Heart, Plus } from 'lucide-react'
import Image from 'next/image'
import { cardAlt, cards, type CollectorCard } from '@/lib/cards'
import type { MediaAsset } from '@/lib/media'
import { media } from '@/lib/media'
import { cn } from '@/lib/utils'

type VisualProps = { active?: boolean }

function CardThumb({ card, className, sizes = '160px' }: { card: CollectorCard; className?: string; sizes?: string }) {
  return (
    <div
      className={cn(
        'relative aspect-[5/7] overflow-hidden rounded-md shadow-[0_10px_20px_-12px_rgba(29,41,36,0.6)]',
        className,
      )}
    >
      <Image src={card.src} alt={cardAlt(card)} fill sizes={sizes} className="object-cover" />
    </div>
  )
}

export function AppScreenshot({ asset }: { asset: MediaAsset }) {
  return (
    <div className="flex size-full items-center justify-center bg-paper-deep p-6 sm:p-10">
      <div className="relative h-full max-h-[620px] aspect-[9/19] overflow-hidden rounded-[2.25rem] border-[6px] border-foreground bg-background shadow-[0_30px_60px_-30px_rgba(29,41,36,0.7)]">
        <Image src={asset.src} alt={asset.alt} fill sizes="320px" className="object-cover object-top" />
      </div>
    </div>
  )
}

export function ScanVisual({ active = true }: VisualProps) {
  return (
    <div className="relative size-full overflow-hidden rounded-[inherit]">
      <Image
        src={media.scan.src}
        alt={media.scan.alt}
        fill
        sizes="(min-width: 1024px) 50vw, 100vw"
        className="object-cover"
      />
      <div aria-hidden className="absolute inset-x-[30%] inset-y-[14%]">
        <span className="absolute left-0 top-0 size-6 border-l-2 border-t-2 border-primary-foreground" />
        <span className="absolute right-0 top-0 size-6 border-r-2 border-t-2 border-primary-foreground" />
        <span className="absolute bottom-0 left-0 size-6 border-b-2 border-l-2 border-primary-foreground" />
        <span className="absolute bottom-0 right-0 size-6 border-b-2 border-r-2 border-primary-foreground" />
        {active && (
          <span className="animate-scanline absolute inset-x-2 h-0.5 bg-primary shadow-[0_0_18px_4px_rgba(224,82,44,0.6)]" />
        )}
      </div>
      <div className="absolute bottom-5 left-5 right-5 w-fit rounded-full bg-background/95 px-4 py-2 text-sm font-medium">
        <span className="mr-2 inline-block size-2 rounded-full bg-primary" aria-hidden />
        Beispiel: Kartenerkennung · Ergebnis überprüfen
      </div>
    </div>
  )
}

const variants = ['Normal', 'Holo', 'Reverse Holo']

export function CollectVisual() {
  const rows = [cards[0], cards[2], cards[4]]
  return (
    <div className="flex size-full flex-col bg-paper-deep p-5 sm:p-8">
      <div className="flex flex-wrap items-center gap-2" aria-hidden>
        {['Sets', 'Varianten', 'Ordner'].map((tab, i) => (
          <span
            key={tab}
            className={cn(
              'rounded-full px-3.5 py-1.5 text-xs font-medium',
              i === 1 ? 'bg-foreground text-background' : 'bg-background/70 text-foreground/70',
            )}
          >
            {tab}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">Schematische Vorschau – echte Varianten werden in der App getrennt erfasst.</p>
      {/* Thumb width is derived from both available width and height so the rows never overflow the frame */}
      <div className="mt-5 min-h-0 flex-1 [container-type:size]">
        <div
          className="flex h-full flex-col justify-center gap-2.5"
          style={{
            ['--thumb' as string]:
              'min(calc((100cqh - 1.25rem - 3 * 0.625rem - 3 * 1.5rem) / 3 * 5 / 7), calc((100cqw - 6.5rem - 1.5rem - 2 * 0.5rem) / 3))',
          }}
        >
          <div className="flex h-5 items-end justify-end gap-2 px-3" aria-hidden>
            {variants.map((variant) => (
              <span key={variant} className="w-[var(--thumb)] text-center text-[11px] leading-[1.1] text-muted-foreground">
                {variant}
              </span>
            ))}
          </div>
          {rows.map((card) => (
            <div key={card.id} className="flex items-center gap-3 rounded-2xl bg-background/70 p-3">
              <p className="min-w-0 flex-1 font-serif text-lg italic leading-tight sm:text-xl">{card.name}</p>
              <ul className="flex gap-2">
                {variants.map((variant, v) => (
                  <li key={variant}>
                    <CardThumb
                      card={card}
                      className={cn(
                        'w-[var(--thumb)]',
                        v === 1 && 'ring-2 ring-primary/70',
                        v === 2 && 'saturate-[1.3]',
                      )}
                      sizes="120px"
                    />
                    <span className="sr-only">{variant}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function MarketVisual({ active = true }: VisualProps) {
  return (
    <div className="flex size-full flex-col bg-sky p-5 sm:p-8">
      <div className="flex flex-1 items-center gap-6 sm:gap-8">
        <CardThumb card={cards[4]} className="w-[36%] shrink-0 -rotate-3 rounded-lg" sizes="220px" />
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.18em] text-foreground/60">Marktpreise · Vorschau</p>
          <p className="mt-1 font-serif text-3xl leading-none">{cards[4].name}</p>
          <svg
            viewBox="-6 0 312 160"
            overflow="visible"
            className="mt-6 w-full"
            role="img"
            aria-label="Schematische Darstellung eines Preisverlaufs"
          >
            {[40, 80, 120].map((y) => (
              <line key={y} x1="0" x2="300" y1={y} y2={y} stroke="currentColor" strokeOpacity="0.12" />
            ))}
            <path
              d="M0 128 C 30 120, 50 136, 80 112 S 130 84, 160 96 S 220 52, 250 46 S 290 26, 300 22"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="3"
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={1}
              className={active ? 'animate-draw' : undefined}
            />
          </svg>
          <div className="mt-6 grid grid-cols-2 gap-3" aria-hidden>
            {['Einzelkarte', 'Sammlungswert'].map((label) => (
              <div key={label} className="rounded-xl bg-background/70 p-3">
                <p className="text-[11px] text-muted-foreground">{label}</p>
                <span className="mt-2 block h-2.5 w-2/3 rounded-full bg-foreground/15" />
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-4 text-xs text-foreground/60">Schematische Darstellung – keine echten Marktdaten.</p>
    </div>
  )
}

export function MissingVisual() {
  const slots: (CollectorCard | null)[] = [cards[0], null, cards[2], cards[1], cards[4], null, null, cards[3], null, cards[0], null, cards[2]]
  const wished = new Set([1, 6])
  return (
    <div className="flex size-full flex-col bg-sage p-5 sm:p-8">
      <div className="flex items-baseline justify-between gap-4">
        <p className="font-serif text-2xl italic">Fehlkarten im Set</p>
        <p className="text-xs text-foreground/60">Beispielansicht</p>
      </div>
      <div className="mt-5 min-h-0 flex-1 [container-type:size]">
      <ul
        className="grid h-full grid-cols-[repeat(4,var(--slot))] content-center justify-center gap-2.5"
        style={{
          ['--slot' as string]:
            'min(calc((100cqw - 3 * 0.625rem) / 4), calc((100cqh - 2 * 0.625rem) / 3 * 5 / 7))',
        }}
      >
        {slots.map((card, i) => (
          <li key={i} className="relative">
            {card ? (
              <CardThumb card={card} className="w-full" sizes="110px" />
            ) : (
              <div className="flex aspect-[5/7] w-full items-center justify-center rounded-md border-[1.5px] border-dashed border-foreground/30 bg-background/30 text-foreground/40">
                {wished.has(i) ? (
                  <span className="inline-flex size-8 items-center justify-center rounded-full bg-background">
                    <Heart className="size-4 fill-primary text-primary" aria-hidden />
                    <span className="sr-only">Fehlt – auf der Wunschliste</span>
                  </span>
                ) : (
                  <>
                    <Plus className="size-4" aria-hidden />
                    <span className="sr-only">Fehlt noch</span>
                  </>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
      </div>
      <div className="mt-5 flex items-center gap-2 text-sm">
        <Heart className="size-4 fill-primary text-primary" aria-hidden />
        <span>Wunschlisten-Vorschau · echte Setansichten folgen.</span>
      </div>
    </div>
  )
}
