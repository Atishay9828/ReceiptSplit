import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReceiptUpload } from "@/components/receipt-upload";

// --- Mocks ---

const mockUploadReceipt = vi.fn();
const mockGetOcrJob = vi.fn();
const mockGetParsedReceipt = vi.fn();
const mockUpdateParsedReceipt = vi.fn();
const mockConfirmParsedReceipt = vi.fn();

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
  adjustments: [
    { type: "tax" as const, label: "Tax", amount_paise: 2500, allocation_method: "proportional" }
  ],
  calculated_total_paise: 27500,
  difference_paise: 0,
  review_fingerprint: "a".repeat(64),
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
    expect(screen.getByText(/Review the items, taxes, and charges/)).toBeTruthy();
    expect(screen.getByText(/A receipt detail needs checking/)).toBeTruthy();

    // Merchant
    expect(screen.getByDisplayValue("Test Restaurant")).toBeTruthy();
  });

  it("uploads images for authenticated server OCR without PaddleOCR", async () => {
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

    expect(mockUploadReceipt).toHaveBeenCalledWith(
      ROOM_ID,
      TOKEN,
      pngFile,
      undefined,
      expect.any(AbortSignal)
    );
  });

  it("requires fresh acknowledgment when reviewed values change a discrepancy", async () => {
    const mismatched = {
      ...MOCK_DRAFT,
      total_paise: 28000,
      difference_paise: -500,
      needs_review: true,
      warnings: ["items_sum_mismatch"]
    };
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1", image_id: "img-1", job_id: "job-1", status: "succeeded", parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(mismatched);

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["receipt"], "receipt.png", { type: "image/png" })] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));
    await waitFor(() => expect(screen.getByTestId("ocr-draft-review")).toBeTruthy());

    const confirm = screen.getByRole("button", { name: /Confirm into room/ });
    expect(confirm).toBeDisabled();
    const acknowledgment = screen.getByRole("checkbox", {
      name: "Use the reviewed bill total despite this difference."
    });
    expect(acknowledgment).not.toBeChecked();
    fireEvent.click(acknowledgment);
    expect(confirm).not.toBeDisabled();

    fireEvent.change(screen.getByDisplayValue("150.00"), { target: { value: "160.00" } });
    expect(acknowledgment).not.toBeChecked();
    expect(confirm).toBeDisabled();
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
    expect(mockConfirmParsedReceipt).toHaveBeenCalledWith(
      ROOM_ID,
      TOKEN,
      "parsed-1",
      { accept_unreconciled_total: false, review_fingerprint: "a".repeat(64) },
      expect.any(AbortSignal)
    );
  });

  it("keeps success when the parent refresh fails", async () => {
    onConfirmed.mockRejectedValueOnce(new Error("offline"));
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1", image_id: "img-1", job_id: "job-1", status: "succeeded", parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);
    mockUpdateParsedReceipt.mockResolvedValue(MOCK_DRAFT);
    mockConfirmParsedReceipt.mockResolvedValue({
      parsed_receipt_id: "parsed-1", status: "confirmed", already_confirmed: false,
      created_item_ids: ["item-1"], created_adjustment_ids: [], events: []
    });

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["receipt"], "receipt.png", { type: "image/png" })] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));
    await waitFor(() => expect(screen.getByTestId("ocr-draft-review")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Confirm into room/ }));

    await waitFor(() => expect(screen.getByText("Receipt added; refresh needed.")).toBeTruthy());
    expect(screen.getByText(/1 item added to room from receipt/)).toBeTruthy();
    expect(mockConfirmParsedReceipt).toHaveBeenCalledTimes(1);
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

  it("reset releases the saving state when it aborts a draft update", async () => {
    mockUploadReceipt.mockResolvedValue({
      receipt_id: "receipt-1", image_id: "img-1", job_id: "job-1", status: "succeeded", parsed_receipt_id: "parsed-1"
    });
    mockGetParsedReceipt.mockResolvedValue(MOCK_DRAFT);
    mockUpdateParsedReceipt.mockImplementation(
      (_roomId: string, _token: string, _id: string, _payload: unknown, signal: AbortSignal) =>
        new Promise((_resolve, reject) => {
          signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
        })
    );

    render(<ReceiptUpload roomId={ROOM_ID} token={TOKEN} onConfirmed={onConfirmed} />);
    const input = document.getElementById("receipt-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["receipt"], "receipt.png", { type: "image/png" })] } });
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));
    await waitFor(() => expect(screen.getByTestId("ocr-draft-review")).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));

    expect(screen.getByText(/Tap to select a receipt image/)).toBeTruthy();
    const resetInput = document.getElementById("receipt-file-input") as HTMLInputElement;
    expect(resetInput.value).toBe("");
    fireEvent.change(resetInput, { target: { files: [new File(["receipt again"], "receipt-again.png", { type: "image/png" })] } });
    expect(screen.getByRole("button", { name: /Scan receipt/ })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /Scan receipt/ }));
    await waitFor(() => expect(screen.getByTestId("ocr-draft-review")).toBeTruthy());
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
  });
});
