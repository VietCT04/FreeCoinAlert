"use client";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { PriceAlertForm } from "./price-alert-form";
import { PriceAlertList } from "./price-alert-list";
import { usePriceAlerts } from "./use-price-alerts";

export function PriceAlertPanel() {
  const { csrfToken, refreshSession, status } = useAuth();
  const markets = useMarkets(status);
  const alerts = usePriceAlerts({ authStatus: status, csrfToken, refreshSession });
  if (status !== "authenticated") return null;
  const readyMarkets = markets.markets.filter((market) => market.status === "available");
  return <section aria-labelledby="price-alerts-heading" className="space-y-5 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700"><div><h2 className="text-xl font-semibold" id="price-alerts-heading">Price alerts</h2><p className="text-sm text-zinc-600 dark:text-zinc-300">Create a one-time alert for a supported market.</p></div>
    {alerts.isInitialLoading ? <p aria-live="polite">Loading your price alerts…</p> : null}
    {markets.error ? <div className="space-y-2"><p>Price alerts are temporarily unavailable because supported market information is not ready.</p><button className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700" onClick={() => void markets.refreshMarkets()} type="button">Retry markets</button></div> : null}
    {!markets.error && !markets.isLoading && !readyMarkets.length ? <div className="space-y-2"><p>Price alerts are temporarily unavailable because supported market information is not ready.</p><button className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700" onClick={() => void markets.refreshMarkets()} type="button">Retry markets</button></div> : null}
    {readyMarkets.length ? <PriceAlertForm connection={alerts.connection} isCreating={alerts.isCreating} markets={markets.markets} onCreate={alerts.create} /> : null}
    {alerts.hasPendingDeliveryPastLimit ? <p>Telegram delivery is still pending. Refresh alerts for the latest status.</p> : null}
    <div className="space-y-3 border-t border-zinc-200 pt-5 dark:border-zinc-700"><div className="flex items-center justify-between gap-3"><h3 className="text-lg font-semibold">Your alerts</h3><button className="rounded-lg border border-zinc-300 px-3 py-2 disabled:opacity-60 dark:border-zinc-700" disabled={alerts.isRefreshing} onClick={() => void alerts.refreshAlerts()} type="button">{alerts.isRefreshing ? "Refreshing…" : "Refresh alerts"}</button></div><div aria-live="polite">{!alerts.isInitialLoading ? <PriceAlertList alerts={alerts.alerts} isLoadingMore={alerts.isLoadingMore} nextCursor={alerts.nextCursor} onDelete={alerts.remove} onLoadMore={alerts.loadMore} /> : null}</div></div>
    {alerts.error ? <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">{alerts.error}</p> : null}
  </section>;
}
