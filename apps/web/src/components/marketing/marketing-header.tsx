import Link from "next/link";

import { MarketingMobileNav } from "@/components/marketing/marketing-mobile-nav";
import { Button } from "@/components/ui/button";

export function MarketingHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
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
            Backtest
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/strategy-alerts">
            Alerts
          </Link>
          <Link className="transition-colors hover:text-foreground" href="/guides">
            Guides
          </Link>
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Button asChild size="sm" variant="ghost">
            <Link href="/sign-in">Sign in</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/sign-up">Start free</Link>
          </Button>
        </div>

        <MarketingMobileNav />
      </div>
    </header>
  );
}
