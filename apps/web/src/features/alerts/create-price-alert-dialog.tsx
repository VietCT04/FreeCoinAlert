"use client";

import { useState } from "react";

import { InlineError } from "@/components/inline-error";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import type { SupportedMarket } from "../markets/types";
import type { TelegramConnection } from "../telegram/types";
import { PriceAlertForm } from "./price-alert-form";
import type { CreatePriceAlertRequest } from "./types";

type CreatePriceAlertDialogProps = {
  connection: TelegramConnection | null;
  disabled?: boolean;
  error?: string | null;
  isCreating: boolean;
  markets: SupportedMarket[];
  onCreate: (request: CreatePriceAlertRequest) => Promise<boolean>;
  onOpenChange?: (open: boolean) => void;
};

export function CreatePriceAlertDialog({
  connection,
  disabled = false,
  error,
  isCreating,
  markets,
  onCreate,
  onOpenChange,
}: CreatePriceAlertDialogProps) {
  const [open, setOpen] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && isCreating) {
      return;
    }
    setOpen(nextOpen);
    onOpenChange?.(nextOpen);
  }

  function closeAfterSuccess() {
    setOpen(false);
    onOpenChange?.(false);
  }

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogTrigger asChild>
        <Button disabled={disabled} type="button">
          Create alert
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100svh-2rem)] w-[calc(100%-2rem)] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create price alert</DialogTitle>
          <DialogDescription>
            Create a one-time crossing alert for a supported Binance Spot market.
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <InlineError message={error} title="Price alert request failed" />
        ) : null}
        <PriceAlertForm
          connection={connection}
          isCreating={isCreating}
          markets={markets}
          onCreate={onCreate}
          onCreated={closeAfterSuccess}
        />
        <DialogFooter>
          <Button
            disabled={isCreating}
            onClick={() => handleOpenChange(false)}
            type="button"
            variant="outline"
          >
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
