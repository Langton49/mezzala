"use client";
import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

// Just the "write one query param, or drop it entirely when the value is
// null" plumbing, shared by anything that needs its nav state (round, date,
// matchday/by-date sub-tab, ...) to survive a reload the same way league/tab
// already do in DashboardContext — router.replace, not push, so navigating
// doesn't fill up browser history one entry per click.
export function useUrlParamSetter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  return useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === null) params.delete(key);
      else params.set(key, value);
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams]
  );
}
