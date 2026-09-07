import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cardyssey",
  description: "Cardyssey – deine Plattform für TCG-Sammlung, Sets, Wishlist, Freunde und Marketplace"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="de"><body>{children}</body></html>;
}
