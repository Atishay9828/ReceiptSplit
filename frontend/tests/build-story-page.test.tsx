import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BuildStoryPage from "@/app/build/page";

describe("ReceiptSplit build story", () => {
  it("turns the shipped product into an evidence-backed first-person story", () => {
    render(<BuildStoryPage />);

    expect(screen.getByRole("heading", { name: /the hard part wasn't splitting the bill/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /six lessons i would carry/i })).toBeInTheDocument();
    expect(screen.getAllByText(/financial math needs invariants/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/realtime is a delivery path/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/safest payment feature/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/real-device upi behavior/i)).toBeInTheDocument();
  });

  it("keeps the product and source paths available without unsafe payment claims", () => {
    const { container } = render(<BuildStoryPage />);

    expect(screen.getByRole("link", { name: /^product$/i })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /source/i })[0]).toHaveAttribute(
      "href",
      "https://github.com/Atishay9828/ReceiptSplit"
    );
    expect(container.textContent).not.toMatch(/verified paid|payment verified|bank confirmed/i);
  });
});
