import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <span aria-hidden className="relative inline-block h-6 w-5">
        <span className="absolute inset-0 -rotate-12 rounded-[3px] border-[1.5px] border-current" />
        <span className="absolute inset-0 rotate-6 rounded-[3px] bg-primary" />
      </span>
      <span className="font-serif text-2xl leading-none tracking-tight">Cardyssey</span>
    </span>
  )
}
