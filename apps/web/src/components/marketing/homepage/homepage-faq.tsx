import { ChevronDown } from "lucide-react";

import { homepageFaqs } from "./constants";

export function HomepageFaq() {
  return (
    <section
      aria-labelledby="faq-title"
      className="scroll-mt-24 border-b py-20 sm:py-24"
      id="faq"
    >
      <div className="mx-auto w-full max-w-4xl space-y-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Questions
          </p>
          <h2
            className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
            id="faq-title"
          >
            Frequently asked questions
          </h2>
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            Short answers before you start a historical simulation.
          </p>
        </div>

        <div className="divide-y rounded-2xl border bg-card px-5 shadow-sm sm:px-6">
          {homepageFaqs.map(({ answer, question }) => (
            <details className="group" key={question}>
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 py-5 font-medium outline-none marker:hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4">
                <span>{question}</span>
                <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
              </summary>
              <p className="max-w-3xl pb-5 pr-8 text-sm leading-6 text-muted-foreground">{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
