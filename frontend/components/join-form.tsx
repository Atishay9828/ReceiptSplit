"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type JoinFormProps = {
  onJoin: (nickname: string) => Promise<void> | void;
};

export function JoinForm({ onJoin }: JoinFormProps) {
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanNickname = nickname.trim();
    if (!cleanNickname) {
      setError("Nickname is required");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onJoin(cleanNickname);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join room");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <Input
        label="Nickname"
        name="nickname"
        maxLength={30}
        value={nickname}
        onChange={(event) => setNickname(event.target.value)}
      />
      {error ? <p className="text-sm font-medium text-coral">{error}</p> : null}
      <Button type="submit" disabled={submitting}>
        Join room
      </Button>
    </form>
  );
}
