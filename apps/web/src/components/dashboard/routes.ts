import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BellRing,
  ChartNoAxesCombined,
  LayoutDashboard,
  Send,
} from "lucide-react";

export type DashboardRoute = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const dashboardRoutes: DashboardRoute[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/price-alerts", label: "Price Alerts", icon: BellRing },
  { href: "/preset-signals", label: "Preset Signals", icon: Activity },
  {
    href: "/historical-analysis",
    label: "Historical Analysis",
    icon: ChartNoAxesCombined,
  },
  { href: "/telegram", label: "Telegram", icon: Send },
];

export function getDashboardRoute(pathname: string): DashboardRoute {
  return (
    dashboardRoutes.find(
      (route) =>
        pathname === route.href || pathname.startsWith(`${route.href}/`),
    ) ?? dashboardRoutes[0]
  );
}
