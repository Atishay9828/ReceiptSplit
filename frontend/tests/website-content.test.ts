import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  receiptSplitWebsiteContent,
  type EvidenceReference,
  type WebsiteLink
} from "@/lib/website-content";

const repositoryRoot = resolve(process.cwd(), "..");

function allEvidence(): EvidenceReference[] {
  return [
    ...receiptSplitWebsiteContent.proofStrip.flatMap((point) => point.evidence),
    ...receiptSplitWebsiteContent.learnings.themes.flatMap((theme) => theme.evidence)
  ];
}

function allLinks(): WebsiteLink[] {
  return [
    ...receiptSplitWebsiteContent.hero.ctas,
    ...receiptSplitWebsiteContent.close.ctas
  ];
}

describe("ReceiptSplit website content", () => {
  it("keeps the product story compact and structurally complete", () => {
    const themeIds = receiptSplitWebsiteContent.learnings.themes.map((theme) => theme.id);

    expect(receiptSplitWebsiteContent.proofStrip).toHaveLength(4);
    expect(receiptSplitWebsiteContent.flow.steps).toHaveLength(6);
    expect(receiptSplitWebsiteContent.learnings.themes.length).toBeGreaterThanOrEqual(5);
    expect(receiptSplitWebsiteContent.learnings.themes.length).toBeLessThanOrEqual(7);
    expect(new Set(themeIds).size).toBe(themeIds.length);

    for (const theme of receiptSplitWebsiteContent.learnings.themes) {
      expect(theme.proof.length).toBeGreaterThanOrEqual(2);
      expect(theme.evidence.length).toBeGreaterThanOrEqual(2);
      expect(theme.tradeoff.length).toBeGreaterThan(0);
    }
  });

  it("uses only coordinator-safe public payment language", () => {
    const serializedContent = JSON.stringify(receiptSplitWebsiteContent);
    const forbiddenClaims = [
      /\bverified paid\b/i,
      /\bpayment verified\b/i,
      /\bbank confirmed\b/i,
      /\bpayment successful\b/i
    ];

    for (const claim of forbiddenClaims) {
      expect(serializedContent).not.toMatch(claim);
    }

    expect(receiptSplitWebsiteContent.hero.boundary).toBe(
      "ReceiptSplit coordinates the flow. It does not process or verify payments."
    );
  });

  it("keeps fragment CTAs attached to real story sections", () => {
    const sectionIds = new Set<string>([
      receiptSplitWebsiteContent.problem.id,
      receiptSplitWebsiteContent.flow.id,
      receiptSplitWebsiteContent.learnings.id,
      receiptSplitWebsiteContent.evidence.id,
      receiptSplitWebsiteContent.close.id
    ]);

    for (const link of allLinks()) {
      if (link.href.startsWith("#")) {
        expect(sectionIds.has(link.href.slice(1))).toBe(true);
      } else {
        expect(link.external).toBe(true);
        expect(link.href).toMatch(/^https:\/\/github\.com\/Atishay9828\/ReceiptSplit\/?$/);
      }
    }
  });

  it("does not cite evidence paths that are absent from the repository", () => {
    for (const reference of allEvidence()) {
      expect(
        existsSync(resolve(repositoryRoot, reference.repositoryPath)),
        `Missing evidence: ${reference.repositoryPath}`
      ).toBe(true);
    }

    for (const theme of receiptSplitWebsiteContent.learnings.themes) {
      if (theme.visual) {
        expect(
          existsSync(resolve(repositoryRoot, theme.visual.repositoryPath)),
          `Missing visual: ${theme.visual.repositoryPath}`
        ).toBe(true);
      }
    }
  });
});
