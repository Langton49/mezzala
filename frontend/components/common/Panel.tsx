// The bordered-card container ("rounded border, white surface") every list
// and table in this app sits inside — pulled into one place instead of the
// same three classes retyped in five different files.
export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`overflow-hidden rounded-md border border-border bg-card ${className}`}>{children}</div>;
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="p-6 text-center text-sm text-muted-foreground">{children}</div>;
}

// Distinct from EmptyState on purpose — "the backend didn't respond" and
// "this genuinely has nothing in it" need to look different, or a real
// outage reads exactly like an empty league with no way to tell them apart.
export function ErrorState({ children }: { children: React.ReactNode }) {
  return <div className="p-6 text-center text-sm text-live">{children}</div>;
}
