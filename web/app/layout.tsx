import type { Metadata } from "next";
import "./globals.css";
import { ThemeSync } from "@/components/ThemeSync";

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
    description: "Deine TCG-Plattform für Sammlung, Scanner, Wishlist, Marketplace und Community.",
    url: "https://cardyssey.de",
    siteName: "Cardyssey",
    locale: "de_DE",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Cardyssey",
    description: "Deine TCG-Plattform für Sammlung, Scanner, Wishlist, Marketplace und Community.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="de"><body><ThemeSync />{children}</body></html>;
}
