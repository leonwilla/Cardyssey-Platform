import { Logo } from '@/components/logo'

const columns = [
  { title: 'Plattform', links: [{label:'Sammlung',href:'/collection'}, {label:'Kartenscanner',href:'/scan'}, {label:'Marktpreise',href:'/collection'}, {label:'Wunschliste',href:'/wishlist'}] },
  { title: 'Entdecken', links: [{label:'Community',href:'/friends'}, {label:'Shop',href:'https://shop.cardyssey.de/'}] },
  { title: 'Rechtliches', links: [{label:'Impressum',href:'/impressum'}, {label:'Datenschutz',href:'/datenschutz'}] },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-paper-deep/60">
      <div className="mx-auto max-w-7xl px-5 py-16 md:px-8">
        <div className="grid gap-12 md:grid-cols-12">
          <div className="md:col-span-5">
            <Logo />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              Ein Zuhause für deine Sammelkarten – zum Verwalten, Entdecken und Teilen.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title} className="md:col-span-2">
              <h3 className="text-sm font-medium">{col.title}</h3>
              <ul className="mt-4 flex flex-col gap-2.5 text-sm text-muted-foreground">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <a href={l.href} className="hover:text-foreground">
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-16 flex flex-col gap-3 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground md:flex-row md:justify-between">
          <p>© {new Date().getFullYear()} CARDYSSEY</p>
          <p className="max-w-2xl md:text-right">
            Pokémon ist eine Marke von Nintendo, Creatures Inc. und GAME FREAK inc. CARDYSSEY steht
            in keiner offiziellen Verbindung zu diesen Unternehmen. Abgebildete Karten sind
            Illustrationen.
          </p>
        </div>
      </div>
    </footer>
  )
}
