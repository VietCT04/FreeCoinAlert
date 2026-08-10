import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-12 text-sm text-muted-foreground sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_repeat(4,minmax(0,1fr))] lg:px-8 lg:py-14">
        <div className="max-w-xs">
          <Link className="font-semibold text-foreground" href="/">
            FreeCoinAlert
          </Link>
          <p className="mt-3 leading-6">
            Backtest supported strategies, then monitor entry signals. Results
            are historical and hypothetical; FreeCoinAlert does not execute
            trades or promise delivery or profit.
          </p>
        </div>

        <nav aria-label="Product links">
          <h2 className="font-medium text-foreground">Product</h2>
          <ul className="mt-4 space-y-3">
            <li>
              <Link className="hover:text-foreground" href="/crypto-backtesting">
                Backtester
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/strategy-alerts">
                Strategy alerts
              </Link>
            </li>
          </ul>
        </nav>

        <nav aria-label="Learn links">
          <h2 className="font-medium text-foreground">Learn</h2>
          <ul className="mt-4 space-y-3">
            <li>
              <Link className="hover:text-foreground" href="/guides">
                Guides
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/guides/how-to-backtest-crypto-strategy">
                How to backtest crypto
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/guides/backtesting-fees-slippage">
                Fees &amp; slippage
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/#faq">
                FAQ
              </Link>
            </li>
          </ul>
        </nav>

        <nav aria-label="Popular backtest links">
          <h2 className="font-medium text-foreground">Popular backtests</h2>
          <ul className="mt-4 space-y-3">
            <li>
              <Link className="hover:text-foreground" href="/rsi-backtest">
                RSI backtest
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/sma-backtest">
                SMA backtest
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/tp-sl-backtest">
                TP/SL backtest
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/bitcoin-backtest">
                Bitcoin backtest
              </Link>
            </li>
          </ul>
        </nav>

        <nav aria-label="Account links">
          <h2 className="font-medium text-foreground">Account</h2>
          <ul className="mt-4 space-y-3">
            <li>
              <Link className="hover:text-foreground" href="/sign-in">
                Sign in
              </Link>
            </li>
            <li>
              <Link className="hover:text-foreground" href="/sign-up">
                Start free
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
