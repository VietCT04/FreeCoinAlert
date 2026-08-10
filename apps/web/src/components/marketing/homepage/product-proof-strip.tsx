const proofItems = [
  {
    detail: "Controlled market catalogue",
    label: "Binance Spot",
  },
  {
    detail: "Supported technical signals",
    label: "RSI & SMA entries",
  },
  {
    detail: "Configurable hypothetical exits",
    label: "TP / SL exits",
  },
  {
    detail: "Included in historical assumptions",
    label: "Fees + slippage modeled",
  },
  {
    detail: "Informational product boundary",
    label: "No order execution",
  },
] as const;

export function ProductProofStrip() {
  return (
    <section
      aria-label="FreeCoinAlert product facts"
      className="rounded-2xl border bg-muted/20 p-4 sm:p-5"
    >
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:divide-x lg:divide-border">
        {proofItems.map((item) => (
          <li
            className="min-w-0 px-0 first:pl-0 sm:px-4 lg:first:pl-0 lg:last:pr-0"
            key={item.label}
          >
            <p className="text-sm font-semibold">{item.label}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
