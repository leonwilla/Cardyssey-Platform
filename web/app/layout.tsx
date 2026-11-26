import type { Metadata } from "next";
import "./globals.css";
import { ThemeSync } from "@/components/ThemeSync";
import "./app.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://cardyssey.de"),
  title: "Cardyssey",
  description: "Cardyssey – Sammeln, Scannen, Tauschen und Handeln.",
  icons: {
    icon: "/cardyssey-emblem-gold.png",
    apple: "/cardyssey-emblem-gold.png",
  },
  openGraph: {
    title: "Cardyssey",
    description: "Deine TCG-Plattform für Sammlung, Scanner, Wunschliste, Marktplatz und Community.",
    url: "https://cardyssey.de",
    siteName: "Cardyssey",
    locale: "de_DE",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Cardyssey",
    description: "Deine TCG-Plattform für Sammlung, Scanner, Wunschliste, Marktplatz und Community.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const appearanceBootstrap = `try {
    const themes = ['OBSIDIAN_GOLD', 'MIDNIGHT_CYAN', 'ROYAL_VIOLET', 'EMERALD_MINT'];
    const theme = localStorage.getItem('cardyssey.appearance.theme');
    document.documentElement.dataset.theme = themes.includes(theme) ? theme : 'OBSIDIAN_GOLD';
    document.documentElement.dataset.brightness = localStorage.getItem('cardyssey.appearance.brightness') === 'dark' ? 'dark' : 'light';
  } catch {}`;
  return (
    <html lang="de" data-theme="OBSIDIAN_GOLD" data-brightness="light" suppressHydrationWarning>
      <head><script id="cardyssey-appearance" dangerouslySetInnerHTML={{__html:appearanceBootstrap}} /></head>
      <body className="cardysseyApp"><ThemeSync />{children}</body>
    </html>
  );
}
