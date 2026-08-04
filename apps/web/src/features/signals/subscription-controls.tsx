"use client";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

type SubscriptionControlsProps = {
  status: "inactive" | "active" | "disabled";
  isPending: boolean;
  onSubscribe: () => void;
  onAskToDisable: () => void;
};

export function SubscriptionControls({
  status,
  isPending,
  onSubscribe,
  onAskToDisable,
}: SubscriptionControlsProps) {
  if (status === "active") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <StatusBadge status="Subscribed" />
        <Button
          aria-busy={isPending}
          disabled={isPending}
          onClick={onAskToDisable}
          type="button"
          variant="destructive"
        >
          Disable
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <StatusBadge status={status === "disabled" ? "Disabled" : "Not subscribed"} />
      <Button
        aria-busy={isPending}
        disabled={isPending}
        onClick={onSubscribe}
        type="button"
      >
        {isPending ? "Subscribing…" : "Subscribe"}
      </Button>
    </div>
  );
}
