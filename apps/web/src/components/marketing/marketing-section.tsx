import type { ReactNode } from "react";

type MarketingSectionProps = {
  children: ReactNode;
  description?: string;
  eyebrow?: string;
  id: string;
  title: string;
};

export function MarketingSection({
  children,
  description,
  eyebrow,
  id,
  title,
}: MarketingSectionProps) {
  return (
    <section
      aria-labelledby={`${id}-title`}
      className="scroll-mt-24 space-y-8 py-16 sm:py-20"
      id={id}
    >
      <div className="max-w-2xl space-y-3">
        {eyebrow ? (
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h2
          className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
          id={`${id}-title`}
        >
          {title}
        </h2>
        {description ? (
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            {description}
          </p>
        ) : null}
      </div>
      {children}
    </section>
  );
}
