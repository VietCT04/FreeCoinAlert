import Link from "next/link";

import { Button } from "@/components/ui/button";

export function MarketingHeader({ showHomeSections = false }: { showHomeSections?: boolean }) {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <Link
          className="flex shrink-0 items-center gap-2 rounded-lg text-sm font-semibold tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          href="/"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground"
          >
            FC
          </span>
          FreeCoinAlert
        </Link>

        <nav
          aria-label="Marketing navigation"
          className="hidden items-center gap-5 text-sm text-muted-foreground md:flex"
        >
          <Link className="transition-colors hover:text-foreground" href="/crypto-backtesting">
            Crypto backtesting
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/crypto-strategy-tester">
            Strategy tester
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/rsi-backtest">
            RSI backtest
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/strategy-alerts">
            Strategy alerts
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/guides">
            Guides
          </Link>
          {showHomeSections ? (
            <>
              <Link className="transition-colors hover:text-foreground" href="#how-it-works">
                How it works
              </Link>
              <Link className="transition-colors hover:text-foreground" href="#what-you-can-test">
                What you can test
              </Link>
              <Link className="transition-colors hover:text-foreground" href="#faq">
                FAQ
              </Link>
            </>
          ) : null}
        </nav>

        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="ghost">
            <Link href="/sign-in">Sign in</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/sign-up">Sign up</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
