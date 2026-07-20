import type { AuthUser } from "@/types/api";

export type AccountSession = {
  token: string;
  user: AuthUser;
};

const ACCOUNT_KEY = "receiptsplit:account";

export function getAccountSession(): AccountSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACCOUNT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AccountSession;
  } catch {
    return null;
  }
}

export function saveAccountSession(session: AccountSession): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCOUNT_KEY, JSON.stringify(session));
  }
}

export function clearAccountSession(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACCOUNT_KEY);
  }
}
