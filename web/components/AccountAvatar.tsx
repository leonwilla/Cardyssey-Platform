"use client";

import { useState } from "react";
import type { User } from "@/lib/types";

export function AccountAvatar({
  user,
  loading = false,
  className = "",
}: {
  user?: User | null;
  loading?: boolean;
  className?: string;
}) {
  const avatarUrl = user?.avatarUrl?.trim();
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const initial = (user?.displayName || user?.email || "C")
    .trim().charAt(0).toUpperCase() || "C";

  return (
    <div className={["avatar", className].filter(Boolean).join(" ")}>
      {loading ? "·" : avatarUrl && avatarUrl !== failedUrl ? (
        <img
          src={avatarUrl}
          alt=""
          width={36}
          height={36}
          onError={() => setFailedUrl(avatarUrl)}
        />
      ) : initial}
    </div>
  );
}
