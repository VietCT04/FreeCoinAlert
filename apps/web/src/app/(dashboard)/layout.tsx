import type { Metadata } from "next";
import type { ReactNode } from "react";

import { DashboardGate } from "../../components/dashboard/dashboard-gate";

export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <DashboardGate>{children}</DashboardGate>;
}
