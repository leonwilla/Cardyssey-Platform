import "./redesign.css"
import { Closing } from '@/components/closing'
import { Community } from '@/components/community'
import { Hero } from '@/components/hero'
import { Journey } from '@/components/journey'
import { Shop } from '@/components/shop'
import { SiteFooter } from '@/components/site-footer'
import { SiteHeader } from '@/components/site-header'

export default function Page() {
  return (
    <div className="cardysseyRedesign">
      <SiteHeader />
      <main>
        <Hero />
        <Journey />
        <Community />
        <Shop />
        <Closing />
      </main>
      <SiteFooter />
    </div>
  )
}
