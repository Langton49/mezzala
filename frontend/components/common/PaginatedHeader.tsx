// The Previous/label/Next row shared by MatchdayView and DateView — same
// three elements, same behavior, previously copy-pasted between the two.
export function PaginatedHeader({
  label,
  onPrev,
  onNext,
}: {
  label: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="mb-2.5 flex items-center justify-between">
      <button
        onClick={onPrev}
        aria-label="Previous"
        className="rounded border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:bg-muted hover:text-foreground"
      >
        ←
      </button>
      <span className="text-sm font-semibold tracking-tight text-primary">{label}</span>
      <button
        onClick={onNext}
        aria-label="Next"
        className="rounded border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:bg-muted hover:text-foreground"
      >
        →
      </button>
    </div>
  );
}
