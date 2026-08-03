import type { ReactNode } from "react";

import { DashboardGate } from "../../components/dashboard/dashboard-gate";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <DashboardGate>{children}</DashboardGate>;
}
