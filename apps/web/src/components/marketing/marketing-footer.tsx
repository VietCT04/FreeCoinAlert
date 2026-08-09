import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-8 text-sm text-muted-foreground sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div>
          <p className="font-semibold text-foreground">FreeCoinAlert</p>
          <p className="mt-1">Backtest supported strategies, then monitor entry signals.</p>
        </div>
        <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-5 gap-y-2">
          <Link className="hover:text-foreground" href="/crypto-backtesting">
            Crypto backtesting
          </Link>
          <Link className="hover:text-foreground" href="/crypto-strategy-tester">
            Strategy tester
          </Link>
          <Link className="hover:text-foreground" href="/rsi-backtest">
            RSI backtest
          </Link>
          <Link className="hover:text-foreground" href="/strategy-alerts">
            Strategy alerts
          </Link>
          <Link className="hover:text-foreground" href="/guides">
            Guides
          </Link>
          <Link className="hover:text-foreground" href="/#how-it-works">
            How it works
          </Link>
          <Link className="hover:text-foreground" href="/#assumptions">
            Assumptions
          </Link>
          <Link className="hover:text-foreground" href="/#faq">
            FAQ
          </Link>
          <Link className="hover:text-foreground" href="/sign-in">
            Sign in
          </Link>
        </nav>
      </div>
    </footer>
  );
}
