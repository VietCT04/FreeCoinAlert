import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { methodologyAssumptions } from "./constants";

const methodologyLinks = [
  { href: "/guides/backtesting-fees-slippage", label: "Fees and slippage" },
  { href: "/guides/backtesting-vs-forward-testing", label: "Backtesting vs forward testing" },
  { href: "/guides/common-backtesting-mistakes", label: "Common backtesting mistakes" },
] as const;

export function MethodologyDisclosure() {
  return (
    <section
      aria-labelledby="methodology-title"
      className="scroll-mt-24 border-b bg-muted/20 py-20 sm:py-24"
      id="methodology"
    >
      <div className="mx-auto w-full max-w-4xl space-y-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Read the methodology
          </p>
          <h2
            className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
            id="methodology-title"
          >
            How the backtest works
          </h2>
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            The useful details stay available without making the first read a
            wall of implementation notes.
          </p>
        </div>

        <details className="group rounded-2xl border bg-card shadow-sm">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 font-semibold outline-none marker:hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4 sm:px-6">
            <span>Execution assumptions</span>
            <span aria-hidden="true" className="text-xl text-muted-foreground transition-transform group-open:rotate-45">
              +
            </span>
          </summary>
          <div className="border-t px-5 py-5 sm:px-6 sm:py-6">
            <dl className="divide-y">
              {methodologyAssumptions.map((assumption) => (
                <div className="grid gap-1 py-3 sm:grid-cols-[minmax(10rem,0.7fr)_minmax(0,1.3fr)] sm:gap-6" key={assumption.label}>
                  <dt className="text-sm font-medium text-muted-foreground">{assumption.label}</dt>
                  <dd className="text-sm leading-6">{assumption.value}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-6 flex flex-wrap gap-x-4 gap-y-2 border-t pt-5 text-sm">
              {methodologyLinks.map((link) => (
                <Link className="inline-flex items-center gap-1 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" href={link.href} key={link.href}>
                  {link.label}
                  <ArrowUpRight aria-hidden="true" className="size-3.5" />
                </Link>
              ))}
            </div>
          </div>
        </details>
      </div>
    </section>
  );
}
