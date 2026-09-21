// Purely decorative top bar — no navigation, no state. Sidebar handles league
// selection and Ribbon handles the standings/fixtures/stats tabs already.
export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-2.5 border-b border-primary-strong bg-primary px-5 text-primary-foreground">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.4" />
        <path
          d="M12 7.5 15.5 10l-1.3 4h-4.4L8.5 10 12 7.5Z"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-lg font-semibold tracking-tight">Mezzala</span>
      <span className="ml-1 hidden text-sm text-primary-foreground/70 sm:inline">Live scores &amp; fixtures</span>
    </header>
  );
}
