import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BuildJourney } from "@/components/build-journey";

describe("BuildJourney", () => {
  it("renders an evidence-backed product evolution instead of a skill cloud", () => {
    const { container } = render(<BuildJourney />);
    const journey = screen.getByRole("region", {
      name: /what i learned by shipping the whole loop/i
    });

    expect(within(journey).getAllByRole("listitem")).toHaveLength(6);
    expect(within(journey).getByText("Model money before screens.")).toBeInTheDocument();
    expect(within(journey).getByText("Treat OCR as a draft, not an answer.")).toBeInTheDocument();
    expect(
      within(journey).getByText("Coordinate payment without pretending to process it.")
    ).toBeInTheDocument();
    expect(within(journey).getByText(/marked paid, payer confirmed, and disputed states/i)).toBeInTheDocument();
    expect(container.querySelector("details")?.open).toBe(true);
    expect(
      within(journey).queryByText(/verified paid|bank confirmed|payment successful/i)
    ).not.toBeInTheDocument();
  });

  it("uses native disclosure controls that work with touch and keyboard focus", async () => {
    const { container } = render(<BuildJourney />);
    const summaries = Array.from(container.querySelectorAll("summary"));
    const collaborationSummary = summaries[1];
    const collaborationDetails = collaborationSummary.parentElement as HTMLDetailsElement;

    expect(summaries).toHaveLength(6);
    expect(collaborationSummary.tagName).toBe("SUMMARY");
    expect(collaborationDetails.open).toBe(false);

    collaborationSummary.focus();
    expect(collaborationSummary).toHaveFocus();
    await userEvent.click(collaborationSummary);

    expect(collaborationDetails.open).toBe(true);
  });
});
