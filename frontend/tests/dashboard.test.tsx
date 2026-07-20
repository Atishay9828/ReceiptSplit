import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() })
}));

describe("persistent rooms dashboard", () => {
  it("explains account-backed rooms without removing quick anonymous bills", async () => {
    window.localStorage.clear();
    render(<DashboardPage />);

    expect(
      await screen.findByRole("heading", { name: /keep rooms, friends, and bills together/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/individual bill links still work without an account/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/google sign-in is not configured yet/i)).toBeInTheDocument();
  });
});
