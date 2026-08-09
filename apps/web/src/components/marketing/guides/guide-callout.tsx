import type { ReactNode } from "react";

type GuideCalloutProps = {
  children: ReactNode;
  title: string;
  tone?: "info" | "caution";
};

export function GuideCallout({ children, title, tone = "info" }: GuideCalloutProps) {
  const toneClassName =
    tone === "caution"
      ? "border-amber-500/40 bg-amber-500/10"
      : "border-primary/20 bg-primary/5";

  return (
    <aside className={`my-8 rounded-xl border p-5 ${toneClassName}`}>
      <h3 className="text-base font-semibold">{title}</h3>
      <div className="mt-2 space-y-2 text-sm leading-7 text-muted-foreground">
        {children}
      </div>
    </aside>
  );
}
