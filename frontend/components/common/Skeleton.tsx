export function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`skeleton block rounded ${className}`} />;
}
