"use client";

import Image from "next/image";
import { LeagueList } from "./LeagueList";

export function Sidebar() {
  return (
    <aside className="flex w-52 flex-col self-start rounded-md border border-border bg-card py-2">
      <div className="mb-4 pl-5 pr-2.5">
        <Image src="/FullLogo.png" alt="Mezzala" width={919} height={238} className="h-6 w-auto" priority />
      </div>
      <LeagueList />
    </aside>
  );
}
