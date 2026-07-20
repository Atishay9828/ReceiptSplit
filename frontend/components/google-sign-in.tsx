"use client";

import { LogIn } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { saveAccountSession, type AccountSession } from "@/lib/auth-session";

type GoogleCredentialResponse = { credential?: string };

type GoogleAccounts = {
  id: {
    initialize(options: {
      client_id: string;
      callback: (response: GoogleCredentialResponse) => void;
    }): void;
    renderButton(element: HTMLElement, options: Record<string, unknown>): void;
  };
};

declare global {
  interface Window {
    google?: { accounts: GoogleAccounts };
  }
}

export function GoogleSignIn({ onSignedIn }: { onSignedIn: (session: AccountSession) => void }) {
  const target = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !target.current) return;
    const render = () => {
      if (!window.google || !target.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          if (!credential) return;
          setError(null);
          try {
            const user = await api.getMe(credential);
            const session = { token: credential, user };
            saveAccountSession(session);
            onSignedIn(session);
          } catch (signInError) {
            setError(signInError instanceof Error ? signInError.message : "Google sign-in failed");
          }
        }
      });
      target.current.replaceChildren();
      window.google.accounts.id.renderButton(target.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "signin_with",
        shape: "rectangular",
        width: 280
      });
    };

    const existing = document.querySelector<HTMLScriptElement>("script[data-google-identity]");
    if (existing) {
      if (window.google) render();
      else existing.addEventListener("load", render, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.dataset.googleIdentity = "true";
    script.addEventListener("load", render, { once: true });
    document.head.appendChild(script);
  }, [clientId, onSignedIn]);

  if (!clientId) {
    return (
      <div className="rounded-md border border-border bg-cloud p-4 text-sm text-muted">
        <p className="flex items-center gap-2 font-semibold text-ink">
          <LogIn size={17} aria-hidden="true" /> Google sign-in is not configured yet.
        </p>
        <p className="mt-1">Quick one-off receipt rooms still work without an account.</p>
      </div>
    );
  }

  return (
    <div>
      <div ref={target} className="min-h-11" aria-label="Sign in with Google" />
      {error ? <p className="mt-2 text-sm font-semibold text-coral">{error}</p> : null}
    </div>
  );
}
