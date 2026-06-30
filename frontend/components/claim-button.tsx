"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { ClaimPayload } from "@/types/api";

type ClaimButtonProps = {
  itemVersion: number;
  disabled?: boolean;
  onClaim: (payload: ClaimPayload) => Promise<void>;
};

export function ClaimButton({ itemVersion, disabled, onClaim }: ClaimButtonProps) {
  const [submitting, setSubmitting] = useState(false);

  async function claim() {
    setSubmitting(true);
    try {
      await onClaim({ item_version: itemVersion, claimed_qty: 1 });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Button type="button" variant="secondary" disabled={disabled || submitting} onClick={claim}>
      Claim
    </Button>
  );
}
