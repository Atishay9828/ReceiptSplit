"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { RoomCreateRequest, SplitMode } from "@/types/api";

type CreateRoomFormProps = {
  onCreate: (payload: RoomCreateRequest) => Promise<void>;
  submitLabel?: string;
};

export function CreateRoomForm({ onCreate, submitLabel = "Create room" }: CreateRoomFormProps) {
  const [splitMode, setSplitMode] = useState<SplitMode>("item_wise");
  const [payerName, setPayerName] = useState("");
  const [payerVpa, setPayerVpa] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onCreate({
        split_mode: splitMode,
        payer_name: payerName.trim() || undefined,
        payer_vpa: payerVpa.trim() || undefined
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create room");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <Select
        label="Split mode"
        value={splitMode}
        onChange={(event) => setSplitMode(event.target.value as SplitMode)}
      >
        <option value="item_wise">Item-wise</option>
        <option value="equal">Equal</option>
      </Select>
      <Input
        label="Payer name"
        name="payer-name"
        autoComplete="name"
        value={payerName}
        onChange={(event) => setPayerName(event.target.value)}
      />
      <Input
        label="Payer VPA"
        name="payer-vpa"
        placeholder="name@bank"
        value={payerVpa}
        onChange={(event) => setPayerVpa(event.target.value)}
      />
      {error ? <p className="text-sm font-medium text-coral">{error}</p> : null}
      <Button type="submit" size="lg" disabled={submitting}>
        {submitting ? "Creating..." : submitLabel}
      </Button>
    </form>
  );
}
