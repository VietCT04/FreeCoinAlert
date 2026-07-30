"use client";

import { useState } from "react";

import type { PriceAlert } from "./types";

type PriceAlertListProps = { alerts: PriceAlert[]; isLoadingMore: boolean; nextCursor: string | null; onDelete: (id: string) => Promise<boolean>; onLoadMore: () => Promise<void> };

function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.valueOf()) ? "Unknown time" : date.toLocaleString(); }
function lifecycle(alert: PriceAlert): string {
  if (alert.status === "active") return alert.evaluationReady ? "Active · Monitoring" : "Active · Waiting for first live price";
  if (alert.status === "triggered") return "Triggered";
  if (alert.status === "disabled") return "Disabled";
  return "Failed";
}
function delivery(status: PriceAlert["delivery"]["status"]): string {
  return { not_queued: "No Telegram message queued.", queued: "Telegram notification queued.", sending: "Sending Telegram notification…", retrying: "Telegram notification is waiting to retry.", sent: "Telegram accepted the notification.", failed: "Telegram notification could not be sent.", outcome_unknown: "We could not confirm whether Telegram accepted the notification. Check Telegram before taking further action." }[status];
}
function marketWarning(alert: PriceAlert): string | null {
  if (alert.marketData.status === "stale") return "Live market data is delayed. Alert evaluation is temporarily paused.";
  if (alert.marketData.status === "disconnected") return "The market-data connection is unavailable. Alert evaluation will resume after reconnecting.";
  if (alert.marketData.status === "unavailable") return "This market is unavailable. The alert is not being evaluated.";
  return null;
}

export function PriceAlertList({ alerts, isLoadingMore, nextCursor, onDelete, onLoadMore }: PriceAlertListProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  if (!alerts.length) return <p>You have no price alerts yet.</p>;
  async function confirmDelete(id: string) { setDeletingId(id); if (await onDelete(id)) setConfirmingId(null); setDeletingId(null); }
  return <div className="space-y-4"><div className="space-y-3">{alerts.map((alert) => {
    const warning = marketWarning(alert); const canDelete = alert.status === "active" || alert.status === "disabled";
    return <article className="space-y-2 rounded-xl border border-zinc-200 p-4 dark:border-zinc-700" key={alert.id} tabIndex={-1}>
      <h3 className="font-semibold">{alert.market.symbol} · {alert.market.exchange === "binance" ? "Binance" : alert.market.exchange} {alert.market.marketType === "spot" ? "Spot" : alert.market.marketType}</h3>
      <p>Crosses {alert.direction === "cross_above" ? "above" : "below"} {alert.targetPrice} {alert.market.quoteAsset}</p><p>{lifecycle(alert)}</p><p className="text-sm text-zinc-600 dark:text-zinc-300">Created {formatDate(alert.createdAt)}</p>
      {alert.trigger ? <p>Triggered at {alert.trigger.price} {alert.market.quoteAsset} on {formatDate(alert.trigger.occurredAt)}</p> : null}
      {alert.statusReason === "market_disabled" ? <p>This market is no longer available for this alert.</p> : null}
      {alert.statusReason === "evaluation_invariant" ? <p>This alert could not be evaluated safely.</p> : null}
      {alert.statusReason === "user_disabled" ? <p>This alert was disabled.</p> : null}
      {alert.statusReason && !["market_disabled", "evaluation_invariant", "user_disabled"].includes(alert.statusReason) ? <p>This alert has a status update.</p> : null}
      {alert.status === "triggered" ? <p>Telegram: {delivery(alert.delivery.status)}</p> : null}{warning ? <p>{warning}</p> : null}
      {canDelete ? (confirmingId === alert.id ? <div className="space-y-2"><p>Delete this price alert? It will stop being evaluated and cannot be restored.</p><div className="flex gap-3"><button className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700" disabled={deletingId === alert.id} onClick={() => setConfirmingId(null)} type="button">Cancel</button><button className="rounded-lg bg-red-700 px-3 py-2 text-white disabled:opacity-60" disabled={deletingId === alert.id} onClick={() => void confirmDelete(alert.id)} type="button">{deletingId === alert.id ? "Deleting…" : "Confirm delete"}</button></div></div> : <button className="rounded-lg border border-red-300 px-3 py-2 text-red-800 dark:border-red-900 dark:text-red-300" onClick={() => setConfirmingId(alert.id)} type="button">Delete alert</button>) : null}
    </article>;
  })}</div>{nextCursor ? <button className="rounded-lg border border-zinc-300 px-4 py-2 disabled:opacity-60 dark:border-zinc-700" disabled={isLoadingMore} onClick={() => void onLoadMore()} type="button">{isLoadingMore ? "Loading…" : "Load more"}</button> : null}</div>;
}
