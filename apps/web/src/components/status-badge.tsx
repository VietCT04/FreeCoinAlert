import { Badge, badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

const successStatuses = new Set([
  "active",
  "available",
  "connected",
  "completed",
  "ready",
  "succeeded",
  "triggered",
]);

const warningStatuses = new Set([
  "degraded",
  "linking",
  "pending",
  "processing",
  "queued",
  "running",
  "stale",
]);

const destructiveStatuses = new Set([
  "cancelled",
  "disabled",
  "disconnected",
  "expired",
  "failed",
  "unavailable",
]);

function statusVariant(status: string): BadgeVariant {
  const normalizedStatus = status.trim().toLowerCase();

  if (successStatuses.has(normalizedStatus)) return "success";
  if (warningStatuses.has(normalizedStatus)) return "warning";
  if (destructiveStatuses.has(normalizedStatus)) return "destructive";
  return "outline";
}

type StatusBadgeProps = {
  status: string;
  variant?: BadgeVariant;
  className?: string;
};

export function StatusBadge({ status, variant, className }: StatusBadgeProps) {
  return (
    <Badge className={className} variant={variant ?? statusVariant(status)}>
      {status}
    </Badge>
  );
}
