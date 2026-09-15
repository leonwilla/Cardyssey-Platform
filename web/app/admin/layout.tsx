import type { ReactNode } from "react";

import { FounderTools } from "./FounderTools";

export default function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <>
      {children}
      <FounderTools />
    </>
  );
}
