import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  supportingText?: ReactNode;
  icon?: ReactNode;
};

export function MetricCard({
  label,
  value,
  supportingText,
  icon,
}: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        {icon ? (
          <span aria-hidden="true" className="text-muted-foreground">
            {icon}
          </span>
        ) : null}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        {supportingText ? (
          <p className="mt-1 text-xs text-muted-foreground">{supportingText}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
