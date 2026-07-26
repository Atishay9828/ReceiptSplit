import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleSignIn } from "@/components/google-sign-in";
import { api } from "@/lib/api";

describe("Google sign-in", () => {
  const originalClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    document.querySelectorAll("script[data-google-identity]").forEach((script) => script.remove());
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "google-client-id";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = originalClientId;
    delete window.google;
  });

  it("exchanges the Google credential for an account session", async () => {
    let credentialCallback: ((response: { credential?: string }) => void) | undefined;
    const initialize = vi.fn(
      (options: {
        client_id: string;
        callback: (response: { credential?: string }) => void;
      }) => {
        credentialCallback = options.callback;
      }
    );
    const renderButton = vi.fn((target: HTMLElement) => {
      target.textContent = "Sign in with Google";
    });
    window.google = {
      accounts: {
        id: {
          initialize,
          renderButton
        }
      }
    };

    const account = {
      id: "user-aj",
      provider: "google",
      subject: "google-aj",
      email: "aj@example.com",
      username: "aj",
      display_name: "AJ"
    };
    vi.spyOn(api, "getMe").mockResolvedValue(account);
    const onSignedIn = vi.fn();

    render(<GoogleSignIn onSignedIn={onSignedIn} />);

    const identityScript = document.querySelector<HTMLScriptElement>(
      "script[data-google-identity]"
    );
    expect(identityScript).not.toBeNull();
    act(() => {
      identityScript?.dispatchEvent(new Event("load"));
    });
    await waitFor(() => expect(initialize).toHaveBeenCalledTimes(1));
    act(() => credentialCallback?.({ credential: "google-id-token" }));

    await waitFor(() => expect(api.getMe).toHaveBeenCalledWith("google-id-token"));
    await waitFor(() =>
      expect(onSignedIn).toHaveBeenCalledWith({ token: "google-id-token", user: account })
    );
    expect(JSON.parse(window.localStorage.getItem("receiptsplit:account") ?? "{}")).toEqual({
      token: "google-id-token",
      user: account
    });
  });
});
