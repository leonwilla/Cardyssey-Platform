'use client'

import { useState } from 'react'
import { TiltCard } from '@/components/tilt-card'
import { cardAlt, cards } from '@/lib/cards'

export function CardFan() {
  const [active, setActive] = useState(2)
  const [hovered, setHovered] = useState<number | null>(null)
  const [spread, setSpread] = useState(false)
  const activeCard = cards[active]

  return (
    <div className="flex flex-col items-center">
      <div
        className="relative mx-auto h-[min(118vw,460px)] w-full max-w-2xl sm:h-[560px] lg:h-[600px]"
        onPointerEnter={() => setSpread(true)}
        onPointerLeave={() => {
          setSpread(false)
          setHovered(null)
        }}
      >
        <div
          aria-hidden
          className="absolute left-1/2 top-1/2 size-[80%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-sky"
        />
        <div
          aria-hidden
          className="absolute left-1/2 top-1/2 size-[94%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-foreground/20"
        />

        {cards.map((card, i) => {
          const offset = i - active
          const step = spread ? 1 : 0.72
          const x = offset * 36 * step
          const rotate = offset * 9 * step
          const y = Math.abs(offset) * 14 * step
          const isActive = i === active
          const lift = isActive ? -4 : hovered === i ? -7 : 0

          return (
            <button
              key={card.id}
              type="button"
              onClick={() => setActive(i)}
              onPointerEnter={() => setHovered(i)}
              onPointerLeave={() => setHovered((h) => (h === i ? null : h))}
              aria-label={`${card.name} nach vorne holen`}
              aria-pressed={isActive}
              className="card-fan-item absolute left-1/2 top-1/2 w-[46%] max-w-[290px] rounded-[4.5%/3.2%] transition-transform duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary motion-reduce:transition-none"
              style={{
                transform: `translate(-50%, -50%) translate(${x}%, ${y + lift}%) rotate(${rotate}deg) scale(${isActive ? 1.06 : hovered === i ? 0.98 : 0.94})`,
                zIndex: 10 - Math.abs(offset),
              }}
            >
              <TiltCard
                src={card.src}
                alt={cardAlt(card)}
                priority={Math.abs(offset) <= 1}
                intensity={isActive ? 16 : 8}
                sizes="(min-width: 1024px) 290px, 46vw"
              />
            </button>
          )
        })}
      </div>

      <div className="mt-4 flex items-center gap-4" aria-live="polite">
        <span className="font-serif text-2xl italic">{activeCard.name}</span>
        <span className="h-px w-8 bg-foreground/30" aria-hidden />
        <span className="text-sm text-muted-foreground">Typ {activeCard.type}</span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Tippe auf eine Karte, um sie nach vorne zu holen.</p>
    </div>
  )
}
