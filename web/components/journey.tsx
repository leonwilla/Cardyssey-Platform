'use client'

import { useEffect, useRef, useState } from 'react'
import {
  AppScreenshot,
  CollectVisual,
  MarketVisual,
  MissingVisual,
  ScanVisual,
} from '@/components/journey-visuals'
import { appScreenshots } from '@/lib/media'
import { cn } from '@/lib/utils'

type StepId = keyof typeof appScreenshots

type Step = {
  id: StepId
  title: string
  kicker: string
  text: string
  Visual: React.ComponentType<{ active?: boolean }>
}

const steps: Step[] = [
  {
    id: 'scannen',
    title: 'Scannen',
    kicker: 'Mit dem Smartphone',
    text: 'Scanne Pokémon-Karten, überprüfe das Erkennungsergebnis und wähle die passende Variante, bevor du sie deiner Sammlung hinzufügst.',
    Visual: ScanVisual,
  },
  {
    id: 'sammeln',
    title: 'Sammeln',
    kicker: 'Karten, Sets & Varianten',
    text: 'Verwalte deine Karten nach Sets und Varianten, filtere deine Sammlung und behalte doppelte Exemplare im Blick.',
    Visual: CollectVisual,
  },
  {
    id: 'marktpreise',
    title: 'Marktpreise',
    kicker: 'Werte im Blick',
    text: 'Sieh verfügbare Marktpreise aus unterstützten Quellen. Bei wenigen eBay-Verkäufen der letzten 30 Tage kennzeichnen wir die geringe Datenbasis.',
    Visual: MarketVisual,
  },
  {
    id: 'wunschliste',
    title: 'Fehlkarten & Wunschliste',
    kicker: 'Was dir noch fehlt',
    text: 'Organisiere gesuchte Karten in deiner Wunschliste. Der automatische Abgleich von Fehlkarten mit dem Shop ist als Erweiterung geplant.',
    Visual: MissingVisual,
  },
]

function StepPreview({ step, active }: { step: Step; active: boolean }) {
  const screenshot = appScreenshots[step.id]
  return screenshot ? <AppScreenshot asset={screenshot} /> : <step.Visual active={active} />
}

export function Journey() {
  const [active, setActive] = useState(0)
  const refs = useRef<(HTMLElement | null)[]>([])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.index))
        }
      },
      { rootMargin: '-45% 0px -45% 0px' },
    )
    refs.current.forEach((el) => el && observer.observe(el))
    return () => observer.disconnect()
  }, [])

  const current = steps[active]

  return (
    <section id="reise" aria-labelledby="reise-title" className="scroll-mt-16 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="max-w-3xl">
          <p className="text-sm text-muted-foreground">So funktioniert&apos;s</p>
          <h2
            id="reise-title"
            className="mt-4 text-balance font-serif text-5xl leading-[0.95] tracking-tight md:text-7xl"
          >
            Eine Sammlung. <em className="text-primary">Vier Momente.</em>
          </h2>
        </div>

        <div className="mt-14 grid gap-6 lg:mt-20 lg:grid-cols-12 lg:gap-16">
          <div className="relative lg:col-span-5">
            <div aria-hidden className="absolute bottom-0 left-0 top-0 hidden w-px bg-border lg:block">
              <span
                className="absolute inset-x-0 top-0 bg-primary transition-[height] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] motion-reduce:transition-none"
                style={{ height: `${((active + 1) / steps.length) * 100}%` }}
              />
            </div>

            <ol className="lg:pl-10">
              {steps.map((step, i) => {
                const isActive = active === i
                return (
                  <li
                    key={step.id}
                    id={step.id}
                    ref={(el) => {
                      refs.current[i] = el
                    }}
                    data-index={i}
                    aria-current={isActive ? 'step' : undefined}
                    className="relative scroll-mt-24 border-t border-border py-10 first:border-t-0 lg:flex lg:min-h-[78vh] lg:flex-col lg:justify-center lg:border-t-0 lg:py-0"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        'absolute -left-10 top-1/2 hidden size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 transition-colors duration-500 lg:block',
                        i <= active ? 'border-primary bg-primary' : 'border-border bg-background',
                      )}
                    />
                    <div
                      className={cn(
                        'transition-[opacity,transform] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] motion-reduce:transition-none',
                        isActive ? 'lg:translate-y-0 lg:opacity-100' : 'lg:translate-y-2 lg:opacity-35',
                      )}
                    >
                      <p className="flex items-center gap-3 text-sm text-muted-foreground">
                        <span className="font-serif text-lg italic text-primary">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span className="h-px w-6 bg-foreground/25" aria-hidden />
                        {step.kicker}
                      </p>
                      <h3 className="mt-3 text-balance font-serif text-4xl leading-[1.02] tracking-tight md:text-5xl lg:text-[3.5rem]">
                        {step.title}
                      </h3>
                      <p className="mt-5 max-w-md text-pretty text-lg leading-relaxed text-foreground/75">
                        {step.text}
                      </p>
                    </div>
                    <div className="mt-8 aspect-[4/5] overflow-hidden rounded-3xl sm:aspect-[4/3] lg:hidden">
                      <StepPreview step={step} active />
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>

          <div className="hidden lg:col-span-7 lg:block">
            <div className="sticky top-24 flex h-[calc(100svh-8rem)] max-h-[720px] flex-col gap-4">
              <div className="flex items-center justify-between gap-6 text-sm">
                <p aria-live="polite" className="flex items-baseline gap-3">
                  <span className="font-serif text-lg italic text-primary tabular-nums">
                    {String(active + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')}
                  </span>
                  <span className="font-medium">{current.title}</span>
                </p>
                <div className="flex flex-1 justify-end gap-1.5" aria-hidden>
                  {steps.map((s, i) => (
                    <span key={s.id} className="relative h-1 w-12 overflow-hidden rounded-full bg-foreground/15">
                      <span
                        className={cn(
                          'absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] motion-reduce:transition-none',
                          i <= active ? 'w-full' : 'w-0',
                        )}
                      />
                    </span>
                  ))}
                </div>
              </div>

              <div className="relative flex-1 overflow-hidden rounded-[2rem] bg-paper-deep">
                {steps.map((step, i) => (
                  <div
                    key={step.id}
                    aria-hidden={active !== i}
                    className={cn(
                      'absolute inset-0 rounded-[inherit] transition-[opacity,transform] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)] motion-reduce:transition-opacity',
                      active === i
                        ? 'translate-y-0 scale-100 opacity-100'
                        : cn('pointer-events-none scale-[0.985] opacity-0', i < active ? '-translate-y-3' : 'translate-y-3'),
                    )}
                  >
                    {Math.abs(active - i) <= 1 ? <StepPreview step={step} active={active === i} /> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
