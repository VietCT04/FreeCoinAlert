"use client";

type SubscriptionControlsProps = {
  status: "inactive" | "active" | "disabled";
  isPending: boolean;
  isConfirmingDisable: boolean;
  onSubscribe: () => void;
  onAskToDisable: () => void;
  onCancelDisable: () => void;
  onConfirmDisable: () => void;
};

export function SubscriptionControls({
  status,
  isPending,
  isConfirmingDisable,
  onSubscribe,
  onAskToDisable,
  onCancelDisable,
  onConfirmDisable,
}: SubscriptionControlsProps) {
  if (isConfirmingDisable) {
    return (
      <div className="space-y-3" aria-live="polite">
        <p>
          Disable this signal? New live events for this preset and market will
          stop, but its history will remain available.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
            disabled={isPending}
            onClick={onCancelDisable}
            type="button"
          >
            Cancel
          </button>
          <button
            className="rounded-lg bg-red-700 px-3 py-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
            aria-busy={isPending}
            disabled={isPending}
            onClick={onConfirmDisable}
            type="button"
          >
            {isPending ? "Disabling…" : "Confirm disable"}
          </button>
        </div>
      </div>
    );
  }

  if (status === "active") {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm font-medium">Active</p>
        <button
          className="rounded-lg border border-red-300 px-3 py-2 text-red-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-900 dark:text-red-300"
          disabled={isPending}
          onClick={onAskToDisable}
          type="button"
        >
          Disable
        </button>
      </div>
    );
  }

  if (status === "disabled") {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm font-medium">Disabled</p>
        <button
          className="rounded-lg bg-zinc-900 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
          aria-busy={isPending}
          disabled={isPending}
          onClick={onSubscribe}
          type="button"
        >
          {isPending ? "Subscribing…" : "Subscribe"}
        </button>
      </div>
    );
  }

  return (
    <button
      className="rounded-lg bg-zinc-900 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
      aria-busy={isPending}
      disabled={isPending}
      onClick={onSubscribe}
      type="button"
    >
      {isPending ? "Subscribing…" : "Subscribe"}
    </button>
  );
}
