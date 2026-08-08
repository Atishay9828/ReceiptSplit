import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReceiptUpload } from "@/components/receipt-upload";

// --- Mocks ---

const mockUploadReceipt = vi.fn();
const mockGetOcrJob = vi.fn();
const mockGetParsedReceipt = vi.fn();
const mockUpdateParsedReceipt = vi.fn();
const mockConfirmParsedReceipt = vi.fn();
const mockBrowserOcrEnabled = vi.fn(() => false);
const mockRunBrowserReceiptOcr = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    uploadReceipt: (...args: unknown[]) => mockUploadReceipt(...args),
    getOcrJob: (...args: unknown[]) => mockGetOcrJob(...args),
    getParsedReceipt: (...args: unknown[]) => mockGetParsedReceipt(...args),
    getParsedReceiptDebug: vi.fn(),
    updateParsedReceipt: (...args: unknown[]) => mockUpdateParsedReceipt(...args),
    confirmParsedReceipt: (...args: unknown[]) => mockConfirmParsedReceipt(...args)
  }
}));

vi.mock("@/lib/ocr/browser", () => ({
  isBrowserReceiptOcrEnabled: () => mockBrowserOcrEnabled(),
  runBrowserReceiptOcr: (...args: unknown[]) => mockRunBrowserReceiptOcr(...args)
}));

const ROOM_ID = "room-1";
const TOKEN = "tok-creator";

const MOCK_DRAFT = {
  id: "parsed-1",
  room_id: ROOM_ID,
  receipt_id: "receipt-1",
  ocr_job_id: "job-1",
  merchant_name: "Test Restaurant",
  subtotal_paise: 25000,
  tax_paise: 2500,
  discount_paise: null,
  total_paise: 27500,
  items: [
    { name: "Butter Chicken", quantity: 1, unit_price_paise: 15000, total_paise: 15000, confidence: 0.9 },
    { name: "Naan", quantity: 2, unit_price_paise: 5000, total_paise: 10000, confidence: 0.85 }
  ],
  adjustments: [],
  warnings: ["Low confidence on item 2"],
  confidence: 0.87,
  needs_review: true,
  parser_version: "indian_restaurant_v1",
  status: "draft",
  redacted_raw_text: null
};

describe("ReceiptUpload", () => {
  const onConfirmed = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    vi.clearAllMocks();
    mockBrowserOcrEnabled.mockReturnValue(false);
    // Provide crypto.randomUUID for jsdom
    if (!globalThis.crypto?.randomUUID) {
      Object.defineProperty(globalThis, "crypto", {
        value: {
          ...globalThis.crypto,
          randomUUID: () => `uuid-${Math.random().toString(36).slice(2)}`
        },
        writable: true
      });
    }
  });

  afterEach(cleanup);

  it("renders idle state with file picker", () => {
    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    expect(screen.getByText("Scan Receipt")).toBeTruthy();
    expect(screen.getByText(/Tap to select a receipt image/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Scan receipt/ })).toBeTruthy();
  });

  it("rejects non-image files", () => {
    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pdfFile = new File(["fake"], "document.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });

    expect(screen.getByText("Only PNG and JPEG images are supported.")).toBeTruthy();
  });

  it("rejects files over 5 MiB", () => {
    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    // Match the backend's 5 MiB upload ceiling.
    const bigContent = new Uint8Array(5 * 1024 * 1024 + 1);
    const bigFile = new File([bigContent], "big.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [bigFile] } });

    expect(screen.getByText(/File is too large/)).toBeTruthy();
  });

  it("accepts valid PNG file and enables scan button", () => {
    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });

    expect(screen.getByText("receipt.png")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Scan receipt/ })).not.toBeDisabled();
  });

  it("uploads and shows draft review on sync processing", async () => {
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1",
      image_id: "img-1",
      job_id: "job-1",
      status: "succeeded",
      parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByTestId("ocr-draft-review")).toBeTruthy();
    });

    // Items should be rendered
    expect(screen.getByDisplayValue("Butter Chicken")).toBeTruthy();
    expect(screen.getByDisplayValue("Naan")).toBeTruthy();

    // Warning badge
    expect(screen.getByText(/Needs review/)).toBeTruthy();
    expect(screen.getByText(/Low confidence on item 2/)).toBeTruthy();

    // Merchant
    expect(screen.getByDisplayValue("Test Restaurant")).toBeTruthy();
  });

  it("can send a browser OCR candidate while keeping the draft review gate", async () => {
    const browserCandidate = {
      provider: "paddleocr-js" as const,
      model: "PP-OCRv5",
      language: "en",
      raw_text: "Test Restaurant\nTea 120.00",
      lines: [
        {
          text: "Test Restaurant",
          poly: [
            { x: 10, y: 10 },
            { x: 120, y: 10 },
            { x: 120, y: 30 },
            { x: 10, y: 30 }
          ],
          score: 0.98
        }
      ]
    };
    mockBrowserOcrEnabled.mockReturnValue(true);
    mockRunBrowserReceiptOcr.mockResolvedValue(browserCandidate);
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1",
      image_id: "img-1",
      job_id: "job-1",
      status: "succeeded",
      parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;
    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByTestId("ocr-draft-review")).toBeTruthy();
    });

    expect(mockRunBrowserReceiptOcr).toHaveBeenCalledWith(
      pngFile,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(mockUploadReceipt).toHaveBeenCalledWith(
      ROOM_ID,
      TOKEN,
      pngFile,
      browserCandidate
    );
  });

  it("allows adding and deleting draft lines", async () => {
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1",
      image_id: "img-1",
      job_id: "job-1",
      status: "succeeded",
      parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByTestId("ocr-draft-review")).toBeTruthy();
    });

    // Should have 2 items initially
    expect(screen.getByText("Items (2)")).toBeTruthy();

    // Add a line
    fireEvent.click(screen.getByRole("button", { name: /Add item/ }));
    expect(screen.getByText("Items (3)")).toBeTruthy();

    // Delete last item (item 3)
    const deleteButtons = screen.getAllByRole("button", { name: /Delete item/ });
    fireEvent.click(deleteButtons[deleteButtons.length - 1]);
    expect(screen.getByText("Items (2)")).toBeTruthy();
  });

  it("confirm flow: validates → PATCHes → POSTs confirm → calls onConfirmed", async () => {
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1",
      image_id: "img-1",
      job_id: "job-1",
      status: "succeeded",
      parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);
    mockUpdateParsedReceipt.mockResolvedValue(MOCK_DRAFT);
    mockConfirmParsedReceipt.mockResolvedValue({
      parsed_receipt_id: "parsed-1",
      status: "confirmed",
      already_confirmed: false,
      created_item_ids: ["item-1", "item-2"],
      created_adjustment_ids: [],
      events: ["item.created", "item.created"]
    });

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByTestId("ocr-draft-review")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /Confirm into room/ }));

    await waitFor(() => {
      expect(screen.getByText(/2 items added to room from receipt/)).toBeTruthy();
    });

    // Verify PATCH was called before confirm
    expect(mockUpdateParsedReceipt).toHaveBeenCalledTimes(1);
    expect(mockConfirmParsedReceipt).toHaveBeenCalledTimes(1);

    // Verify onConfirmed was called to refresh room
    expect(onConfirmed).toHaveBeenCalledTimes(1);
  });

  it("shows error when upload fails", async () => {
    mockUploadReceipt.mockRejectedValue(new Error("Server error"));

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeTruthy();
    });

    expect(screen.getByRole("button", { name: /Try again/ })).toBeTruthy();
  });

  it("reset returns to idle state", async () => {
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1",
      image_id: "img-1",
      job_id: "job-1",
      status: "succeeded",
      parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;

    const pngFile = new File(["fake-png"], "receipt.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [pngFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));

    await waitFor(() => {
      expect(screen.getByTestId("ocr-draft-review")).toBeTruthy();
    });

    fireEvent.click(screen.getByRole("button", { name: /Reset/ }));
    expect(screen.getByText(/Tap to select a receipt image/)).toBeTruthy();
  });
});
