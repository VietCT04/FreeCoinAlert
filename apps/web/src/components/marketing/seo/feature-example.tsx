type FeatureExampleProps = {
  label: string;
  rows: readonly { label: string; value: string }[];
  note?: string;
};

export function FeatureExample({ label, rows, note }: FeatureExampleProps) {
  return (
    <div className="rounded-2xl border bg-card p-6 shadow-sm">
      <p className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
        {label}
      </p>
      <dl className="mt-5 grid gap-x-6 gap-y-4 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.label}>
            <dt className="text-sm text-muted-foreground">{row.label}</dt>
            <dd className="mt-1 font-medium text-foreground">{row.value}</dd>
          </div>
        ))}
      </dl>
      {note ? <p className="mt-5 text-sm text-muted-foreground">{note}</p> : null}
    </div>
  );
}
