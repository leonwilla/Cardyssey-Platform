'use client'

import Image from 'next/image'
import { useRef } from 'react'
import { cn } from '@/lib/utils'

type TiltCardProps = {
  src: string
  alt: string
  className?: string
  intensity?: number
  sizes?: string
  priority?: boolean
}

export function TiltCard({
  src,
  alt,
  className,
  intensity = 14,
  sizes = '(min-width: 1024px) 280px, 45vw',
  priority,
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null)

  function handleMove(e: React.PointerEvent<HTMLDivElement>) {
    const el = ref.current
    if (!el || e.pointerType === 'touch') return
    const rect = el.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width
    const py = (e.clientY - rect.top) / rect.height
    el.dataset.active = 'true'
    el.style.setProperty('--ry', `${(px - 0.5) * intensity}deg`)
    el.style.setProperty('--rx', `${(0.5 - py) * intensity}deg`)
    el.style.setProperty('--mx', `${px * 100}%`)
    el.style.setProperty('--my', `${py * 100}%`)
    el.style.setProperty('--holo', '1')
  }

  function handleLeave() {
    const el = ref.current
    if (!el) return
    el.dataset.active = 'false'
    el.style.setProperty('--ry', '0deg')
    el.style.setProperty('--rx', '0deg')
    el.style.setProperty('--holo', '0')
  }

  return (
    <div
      ref={ref}
      onPointerMove={handleMove}
      onPointerLeave={handleLeave}
      className={cn(
        'tilt holo relative aspect-[5/7] overflow-hidden rounded-[4.5%/3.2%] bg-paper-deep shadow-[0_30px_60px_-25px_rgba(29,41,36,0.55),0_8px_18px_-8px_rgba(29,41,36,0.3)]',
        className,
      )}
    >
      <Image src={src} alt={alt} fill sizes={sizes} priority={priority} className="object-cover" />
    </div>
  )
}
