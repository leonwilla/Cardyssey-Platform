'use client'

import { useState } from 'react'

export function NotifyForm() {
  const [sent, setSent] = useState(false)

  if (sent) {
    return (
      <p role="status" className="font-serif text-2xl italic">
        Danke! Wir melden uns, sobald es Neuigkeiten gibt.
      </p>
    )
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setSent(true)
      }}
      className="flex w-full max-w-md flex-col gap-3 sm:flex-row md:justify-self-end"
    >
      <label htmlFor="notify-email" className="sr-only">
        E-Mail-Adresse
      </label>
      <input
        id="notify-email"
        type="email"
        required
        placeholder="deine@email.de"
        autoComplete="email"
        className="h-12 flex-1 rounded-full border border-background/30 bg-transparent px-5 text-background placeholder:text-background/45 focus:border-background focus:outline-none"
      />
      <button
        type="submit"
        className="h-12 rounded-full bg-background px-6 font-medium text-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
      >
        Benachrichtigen
      </button>
    </form>
  )
}
