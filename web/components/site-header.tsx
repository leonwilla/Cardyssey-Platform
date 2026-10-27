'use client'

import { Menu, X } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Logo } from '@/components/logo'

const nav = [
  { href: '/preview-redesign#scannen', label: 'Scanner' },
  { href: '/preview-redesign#sammeln', label: 'Sammlung' },
  { href: '/preview-redesign#marktpreise', label: 'Marktpreise' },
  { href: '/preview-redesign#community', label: 'Community' },
  { href: '/preview-redesign#shop', label: 'Shop' },
]

export function SiteHeader() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    const onResize = () => window.innerWidth >= 1024 && setOpen(false)
    window.addEventListener('keydown', onKey)
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('resize', onResize)
    }
  }, [open])

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-5 md:px-8">
        <Link href="/preview-redesign" aria-label="CARDYSSEY Vorschau-Startseite" className="rounded-md">
          <Logo />
        </Link>

        <nav aria-label="Hauptnavigation" className="hidden lg:block">
          <ul className="flex items-center gap-7 text-sm">
            {nav.map((item) => (
              <li key={item.label}>
                <a href={item.href} className="text-foreground/75 transition-colors hover:text-foreground">
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden items-center gap-5 lg:flex">
          <a href="/login?design=preview" className="text-sm text-foreground/75 hover:text-foreground">
            Anmelden
          </a>
          <a
            href="/login?design=preview"
            className="rounded-full bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-colors hover:bg-primary"
          >
            Zur Sammlung
          </a>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="mobile-nav"
          className="-mr-2 inline-flex size-10 items-center justify-center rounded-full lg:hidden"
        >
          {open ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
          <span className="sr-only">{open ? 'Menü schließen' : 'Menü öffnen'}</span>
        </button>
      </div>

      {open && (
        <nav
          id="mobile-nav"
          aria-label="Mobile Navigation"
          className="max-h-[min(75svh,480px)] overflow-y-auto border-t border-border/60 bg-background shadow-lg lg:hidden"
        >
          <ul className="mx-auto flex max-w-7xl flex-col px-5 py-2 md:px-8">
            {nav.map((item) => (
              <li key={item.label} className="border-b border-border/50 last:border-b-0">
                <a href={item.href} onClick={() => setOpen(false)} className="block py-2.5 text-base font-medium sm:text-lg">
                  {item.label}
                </a>
              </li>
            ))}
            <li className="grid grid-cols-2 gap-2 pt-3 pb-2">
              <a
                href="/login?design=preview"
                onClick={() => setOpen(false)}
                className="block rounded-full border border-foreground/20 px-3 py-2.5 text-center text-xs font-medium sm:text-sm"
              >
                Anmelden
              </a>
              <a
                href="/login?design=preview"
                onClick={() => setOpen(false)}
                className="block rounded-full bg-foreground px-3 py-2.5 text-center text-xs font-medium sm:text-sm text-background"
              >
                Zur Sammlung
              </a>
            </li>
          </ul>
        </nav>
      )}
    </header>
  )
}
