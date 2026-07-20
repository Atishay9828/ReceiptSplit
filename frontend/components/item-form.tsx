"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { parseRupeesToPaise } from "@/lib/money";
import type { ItemPayload } from "@/types/api";

type ItemFormProps = {
  onSubmit: (payload: ItemPayload) => Promise<void>;
};

export function ItemForm({ onSubmit }: ItemFormProps) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanName = name.trim();
    const parsedQuantity = Number.parseInt(quantity, 10);
    if (!cleanName) {
      setError("Item name is required");
      return;
    }
    if (!Number.isInteger(parsedQuantity) || parsedQuantity < 1) {
      setError("Quantity must be at least 1");
      return;
    }

    let totalPaise: number;
    try {
      totalPaise = parseRupeesToPaise(amount);
    } catch {
      setError("Invalid money amount");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ name: cleanName, quantity: parsedQuantity, total_paise: totalPaise });
      setName("");
      setQuantity("1");
      setAmount("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save item");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="grid gap-3" onSubmit={submit}>
      <Input label="Item name" value={name} onChange={(event) => setName(event.target.value)} />
      <div className="grid grid-cols-[96px_1fr] gap-3">
        <Input
          label="Quantity"
          inputMode="numeric"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
        />
        <Input
          label="Amount"
          inputMode="decimal"
          placeholder="120.50"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
      </div>
      {error ? <p className="text-sm font-medium text-coral">{error}</p> : null}
      <Button type="submit" disabled={submitting}>
        Save item
      </Button>
    </form>
  );
}
