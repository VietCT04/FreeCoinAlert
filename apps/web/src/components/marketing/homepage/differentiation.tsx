import { ChartNoAxesCombined, Eye, ShieldCheck } from "lucide-react";

import { differentiationReasons } from "./constants";

const reasonIcons = [ChartNoAxesCombined, Eye, ShieldCheck] as const;

export function Differentiation() {
  return (
    <section
      aria-labelledby="differentiation-title"
      className="scroll-mt-24 border-b py-20 sm:py-24"
      id="why-freecoinalert"
    >
      <div className="mx-auto w-full max-w-6xl space-y-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Why FreeCoinAlert
          </p>
          <h2
            className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
            id="differentiation-title"
          >
            Clarity before action
          </h2>
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            The product keeps testing, interpretation, and monitoring visible
            without turning an alert into a trade.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {differentiationReasons.map((reason, index) => {
            const Icon = reasonIcons[index];

            return (
              <article
                className="rounded-2xl border bg-card p-6 shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md sm:p-8"
                key={reason.title}
              >
                <Icon aria-hidden="true" className="size-6 text-primary" />
                <h3 className="mt-6 font-heading text-xl font-semibold">{reason.title}</h3>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{reason.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
