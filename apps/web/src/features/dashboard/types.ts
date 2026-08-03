import type { TelegramConnection } from "../telegram/types";

export type DashboardMetric<T> = {
  value: T | null;
  error: string | null;
  isLoading: boolean;
};

export type DashboardMarketReadiness = {
  available: number;
  total: number;
};

export type DashboardActivityKind =
  | "price_alert_triggered"
  | "signal_occurred"
  | "signal_invalidated";

export type DashboardActivityItem = {
  id: string;
  kind: DashboardActivityKind;
  title: string;
  description: string;
  occurredAt: string;
  href: string;
  statusLabel: string;
};

export type DashboardActivityState = {
  items: DashboardActivityItem[];
  error: string | null;
  hasPartialFailure: boolean;
  isLoading: boolean;
};

export type DashboardOverviewState = {
  activeAlerts: DashboardMetric<number>;
  activeSubscriptions: DashboardMetric<number>;
  telegram: DashboardMetric<TelegramConnection>;
  markets: DashboardMetric<DashboardMarketReadiness>;
  activity: DashboardActivityState;
  isRefreshing: boolean;
  refresh: () => Promise<void>;
};
