"use client";

// Last-resort catch for a render-time exception that escapes every view's
// own error handling (e.g. a malformed response shape none of them
// anticipated) — without this, an uncaught error blanks the whole app with
// no way back short of a manual reload.
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background px-4 text-center text-foreground">
      <p className="text-sm font-medium">Something went wrong.</p>
      <button
        onClick={reset}
        className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-muted"
      >
        Try again
      </button>
    </div>
  );
}
