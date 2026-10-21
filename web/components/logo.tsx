import Image from 'next/image'
import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <Image src="/cardyssey-emblem-gold.png" alt="" width={34} height={34} className="size-8 object-contain" />
      <span className="font-serif text-2xl leading-none tracking-tight">Cardyssey</span>
    </span>
  )
}
