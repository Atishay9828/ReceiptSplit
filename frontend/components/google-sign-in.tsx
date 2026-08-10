"use client";

import { ArrowRight, LogIn, ShieldCheck } from "lucide-react";
import Link from "next/link";
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
  const [mode, setMode] = useState<"signin" | "invite">("signin");
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || mode !== "signin" || !target.current) return;
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
  }, [clientId, mode, onSignedIn]);

  return (
    <section className="auth-swap-card" aria-label="Account access">
      <div className="auth-swap-tabs" role="tablist" aria-label="Account access options">
        <button type="button" role="tab" aria-selected={mode === "signin"} className={mode === "signin" ? "is-active" : ""} onClick={() => setMode("signin")}>
          <LogIn size={15} aria-hidden="true" /> Sign in
        </button>
        <button type="button" role="tab" aria-selected={mode === "invite"} className={mode === "invite" ? "is-active" : ""} onClick={() => setMode("invite")}>
          Have an invite?
        </button>
      </div>
      {mode === "invite" ? (
        <div className="auth-swap-panel">
          <span className="auth-swap-icon"><ArrowRight size={17} aria-hidden="true" /></span>
          <div><strong>Open a private invite</strong><p>Use the invite form first. Account sign-in is still required before joining a room.</p></div>
          <Link href="/#invite" className="auth-swap-link">Open invite form <ArrowRight size={14} aria-hidden="true" /></Link>
        </div>
      ) : (
        <div className="auth-swap-panel auth-swap-signin">
          <span className="auth-swap-icon"><ShieldCheck size={17} aria-hidden="true" /></span>
          <div className="auth-swap-signin-body">
            <strong>One account for rooms and invites</strong>
            <p>Your room list stays private to your account.</p>
            {!clientId ? (
              <div className="auth-swap-config-warning"><LogIn size={15} aria-hidden="true" /><span>Google sign-in is not configured yet.</span></div>
            ) : (
              <div ref={target} className="auth-swap-google" aria-label="Sign in with Google" />
            )}
          </div>
        </div>
      )}
      {error ? <p className="auth-swap-error" role="alert">{error}</p> : null}
    </section>
  );
}
