"use client";

import { ArrowUpRight, Link2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import "./join-invite-form.css";

export function resolveInvitePath(value: string): string | null {
  const candidate = value.trim();
  if (!candidate) {
    return null;
  }

  try {
    const parsed = new URL(candidate, window.location.origin);
    const match = parsed.pathname.match(/^\/join\/([^/]+)\/?$/);
    if (!match) {
      return null;
    }
    return `/join/${match[1]}`;
  } catch {
    return null;
  }
}

export function JoinInviteForm() {
  const router = useRouter();
  const [invite, setInvite] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const path = resolveInvitePath(invite);
    if (!path) {
      setError("Paste the complete ReceiptSplit invite link you received.");
      return;
    }
    setError(null);
    router.push(path);
  }

  return (
    <form className="join-invite-panel" onSubmit={submit}>
      <div className="join-invite-heading">
        <span className="join-invite-icon" aria-hidden="true">
          <Link2 size={19} />
        </span>
        <div>
          <p>Already invited?</p>
          <h3>Open your split room</h3>
        </div>
      </div>

      <label htmlFor="invite-link">Paste your private invite link</label>
      <div className="join-invite-control">
        <input
          id="invite-link"
          name="invite-link"
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="https://…/join/…"
          value={invite}
          onChange={(event) => setInvite(event.target.value)}
          aria-describedby={error ? "invite-link-error" : "invite-link-help"}
          aria-invalid={Boolean(error)}
        />
        <button type="submit">
          Open invite
          <ArrowUpRight size={17} aria-hidden="true" />
        </button>
      </div>
      {error ? (
        <p className="join-invite-error" id="invite-link-error" role="alert">
          {error}
        </p>
      ) : (
        <p className="join-invite-help" id="invite-link-help">
          The link stays in this browser and opens the existing nickname-first join flow.
        </p>
      )}
    </form>
  );
}
