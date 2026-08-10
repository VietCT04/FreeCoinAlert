import { ArrowRight, BellRing, ChartNoAxesCombined, ListChecks } from "lucide-react";

import { homepageFlowStages } from "./constants";

const stageIcons = [ListChecks, ChartNoAxesCombined, BellRing] as const;

export function ProductFlow() {
  return (
    <section
      aria-labelledby="how-it-works-title"
      className="scroll-mt-24 border-b py-20 sm:py-24"
      id="how-it-works"
    >
      <div className="mx-auto w-full max-w-6xl space-y-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            One focused workflow
          </p>
          <h2
            className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
            id="how-it-works-title"
          >
            Build, backtest, then monitor the entry
          </h2>
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            Keep the historical question precise and the live-monitoring step
            clear.
          </p>
        </div>

        <ol className="grid gap-4 md:grid-cols-3 md:gap-0">
          {homepageFlowStages.map((stage, index) => {
            const Icon = stageIcons[index];

            return (
              <li className="relative md:flex md:pr-8" key={stage.number}>
                {index < homepageFlowStages.length - 1 ? (
                  <ArrowRight
                    aria-hidden="true"
                    className="absolute right-1/2 top-10 hidden size-5 translate-x-1/2 text-muted-foreground/50 md:block"
                  />
                ) : null}
                <div className="relative z-10 flex w-full flex-col gap-5 rounded-2xl border bg-card p-6 shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md md:mr-4">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-semibold text-primary">
                      {stage.number}
                    </span>
                    <Icon aria-hidden="true" className="size-5 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="font-heading text-xl font-semibold">{stage.title}</h3>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {stage.description}
                    </p>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        <p className="max-w-3xl rounded-xl border-l-2 border-primary/50 pl-4 text-sm leading-6 text-muted-foreground">
          Live monitoring watches the supported entry condition only. It does
          not place orders or run the historical take-profit, stop-loss, or
          holding rules as a live position.
        </p>
      </div>
    </section>
  );
}
