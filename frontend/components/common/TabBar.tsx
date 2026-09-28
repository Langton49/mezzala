// The underline-tab pattern used by both the primary Standings/Fixtures/
// Statistics ribbon and the Matchdays/By-date sub-nav inside it — same
// interaction, same visual language, previously two separate copies.
export function TabBar<T extends string>({
  tabs,
  active,
  onChange,
  compact = false,
}: {
  tabs: readonly { key: T; label: string }[];
  active: T;
  onChange: (key: T) => void;
  compact?: boolean;
}) {
  return (
    <div className={`flex gap-1 border-b border-border ${compact ? "" : "bg-card px-2"}`}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`-mb-px border-b-2 px-3 text-sm font-medium transition-colors ${compact ? "py-2" : "py-2.5"} ${
            active === tab.key
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
