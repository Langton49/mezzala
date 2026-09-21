"use client";
import { useState } from "react";
import { teamLogoUrl, leagueLogoUrl } from "@/lib/images";

type LogoKind = "team" | "league";

// Session-wide cache of ids known to have no image (the API returns 204, not
// 404, for a valid id with nothing to serve — see lib/images.ts). Remembering
// that avoids re-requesting the same empty image on every re-render/remount.
const STORAGE_KEY = "mezzala:missing-logos";

function loadMissingSet(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

const missingLogos = loadMissingSet();

function markMissing(key: string) {
  missingLogos.add(key);
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...missingLogos]));
  } catch {
    // sessionStorage unavailable — in-memory Set still prevents repeat
    // flicker for the rest of this session either way.
  }
}

interface LogoProps {
  id: number | null;
  kind: LogoKind;
  alt: string;
  size?: number;
}

export function Logo({ id, kind, alt, size = 24 }: LogoProps) {
  const key = id != null ? `${kind}:${id}` : null;
  const [failed, setFailed] = useState(() => (key ? missingLogos.has(key) : true));

  if (!key || failed) {
    return <Placeholder size={size} alt={alt} />;
  }

  const src = kind === "team" ? teamLogoUrl(id!) : leagueLogoUrl(id!);

  return (
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      loading="lazy"
      decoding="async"
      className="shrink-0 object-contain"
      style={{ width: size, height: size }}
      onError={() => {
        markMissing(key);
        setFailed(true);
      }}
    />
  );
}

function Placeholder({ size, alt }: { size: number; alt: string }) {
  return (
    <svg
      role="img"
      aria-label={alt}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="shrink-0 text-border-strong"
    >
      <path
        d="M12 2.5 4 5.5v6c0 5 3.4 8.8 8 10 4.6-1.2 8-5 8-10v-6l-8-3Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}
