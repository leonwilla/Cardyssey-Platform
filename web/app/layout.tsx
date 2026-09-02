import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cardyssey",
  description: "TCG collection, scanner, sets and market"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="de"><body>{children}</body></html>;
}
