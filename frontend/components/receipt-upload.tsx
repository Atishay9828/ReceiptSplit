"use client";

import {
  AlertTriangle,
  Camera,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Plus,
  RotateCcw,
  Trash2,
  Upload
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatPaise, parseRupeesToPaise } from "@/lib/money";
import type {
  ParsedReceiptAdjustment,
  ParsedReceiptDraftResponse,
  ParsedReceiptLine
} from "@/types/api";

// --- Constants ---

const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg", "image/jpg"]);
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // Must match backend ImageValidationConfig.max_bytes.
const OCR_POLL_INTERVAL_MS = 2000;

type OcrStage =
  | "idle"
  | "uploading"
  | "processing"
  | "draft"
  | "confirming"
  | "confirmed"
  | "error";

type ReceiptUploadProps = {
  roomId: string;
  token: string;
  onConfirmed: () => Promise<void>;
};

// --- Local draft line type for editing ---

type DraftLine = {
  key: string;
  name: string;
  quantity: string;
  amount: string;
  unitPricePaise: number | null;
  confidence: number;
};

type DraftAdjustment = ParsedReceiptAdjustment & { key: string; amount: string };

const ADJUSTMENT_TYPES = [
  "tax",
  "service_charge",
  "delivery_fee",
  "packaging_fee",
  "tip",
  "discount",
  "coupon",
  "offer",
  "adjustment",
  "rounding"
] as const;

const WARNING_LABELS: Record<string, string> = {
  ambiguous_line: "A line could not be read clearly.",
  low_confidence_line: "One or more item lines need checking.",
  invalid_item_amount: "An item amount is outside the supported range and needs checking.",
  invalid_total_amount: "The receipt total is outside the supported range and needs checking.",
  quantity_total_inferred: "The printed line total is clear, but its unit price was not shown.",
  quantity_price_mismatch: "A quantity and unit price do not match the printed line total.",
  items_sum_mismatch: "The reviewed bill total differs from the receipt total.",
  items_subtotal_mismatch: "The reviewed items differ from the receipt subtotal.",
  tax_summary_mismatch: "The tax components differ from the printed tax summary.",
  unresolved_adjustment_amount: "A tax or charge amount needs to be entered.",
  missing_total: "The receipt total could not be read.",
  tax_detected: "Tax was found. Check the adjustment rows.",
  service_charge_detected: "A service charge was found. Check the adjustment rows.",
  discount_detected: "A discount was found. Check the adjustment rows."
};

function adjustmentToDraft(value: ParsedReceiptAdjustment): DraftAdjustment {
  return { ...value, key: crypto.randomUUID(), amount: (value.amount_paise / 100).toFixed(2) };
}

function signedRupeesToPaise(value: string): number {
  const trimmed = value.trim();
  if (trimmed.startsWith("-")) return -parseRupeesToPaise(trimmed.slice(1));
  return parseRupeesToPaise(trimmed);
}

function effectiveAdjustmentAmount(adjustment: DraftAdjustment): number {
  if (["discount", "coupon", "offer"].includes(adjustment.type)) {
    return -Math.abs(adjustment.amount_paise);
  }
  if (["tax", "service_charge", "delivery_fee", "packaging_fee", "tip"].includes(adjustment.type)) {
    return Math.abs(adjustment.amount_paise);
  }
  return adjustment.amount_paise;
}

function adjustmentSum(
  adjustments: ParsedReceiptAdjustment[],
  group: "tax" | "discount"
): number | null {
  const matching = adjustments.filter((adjustment) => group === "tax"
    ? adjustment.type === "tax"
    : ["discount", "coupon", "offer"].includes(adjustment.type));
  if (matching.length === 0) return null;
  return matching.reduce((sum, adjustment) => group === "tax"
    ? sum + Math.abs(adjustment.amount_paise)
    : sum - Math.abs(adjustment.amount_paise), 0);
}

function lineToApi(line: DraftLine): ParsedReceiptLine | null {
  const name = line.name.trim();
  if (!name) return null;
  const qty = Number.parseInt(line.quantity, 10);
  if (!Number.isInteger(qty) || qty < 1) return null;
  let totalPaise: number;
  try {
    totalPaise = parseRupeesToPaise(line.amount);
  } catch {
    return null;
  }
  return {
    name,
    quantity: qty,
    unit_price_paise: line.unitPricePaise,
    total_paise: totalPaise,
    confidence: line.confidence
  };
}

function apiToLine(item: ParsedReceiptLine): DraftLine {
  return {
    key: crypto.randomUUID(),
    name: item.name,
    quantity: String(item.quantity),
    amount: (item.total_paise / 100).toFixed(2),
    unitPricePaise: item.unit_price_paise,
    confidence: item.confidence
  };
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) {
    return "Only PNG and JPEG images are supported.";
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MiB). Maximum is 5 MiB.`;
  }
  return null;
}

let nextKey = 0;
function newBlankLine(): DraftLine {
  return {
    key: `new-${++nextKey}`,
    name: "",
    quantity: "1",
    amount: "",
    unitPricePaise: null,
    confidence: 1.0
  };
}

// --- Component ---

export function ReceiptUpload({ roomId, token, onConfirmed }: ReceiptUploadProps) {
  const [stage, setStage] = useState<OcrStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // OCR tracking
  const [, setJobId] = useState<string | null>(null);
  const [parsedReceiptId, setParsedReceiptId] = useState<string | null>(null);
  const [serverDraft, setServerDraft] = useState<ParsedReceiptDraftResponse | null>(null);
  const requestAbortRef = useRef(new AbortController());

  // Local editable draft state
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [adjustments, setAdjustments] = useState<DraftAdjustment[]>([]);
  const [merchantName, setMerchantName] = useState("");
  const [subtotalAmount, setSubtotalAmount] = useState("");
  const [receiptTotalAmount, setReceiptTotalAmount] = useState("");
  const [acceptDifference, setAcceptDifference] = useState(false);
  const [draftWarnings, setDraftWarnings] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmedCount, setConfirmedCount] = useState(0);

  // Raw text debug
  const [rawText, setRawText] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState(false);
  const [loadingRawText, setLoadingRawText] = useState(false);

  // --- File selection ---

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setFileError(null);
    setError(null);
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const validationError = validateFile(file);
    if (validationError) {
      setFileError(validationError);
      setSelectedFile(null);
      event.target.value = "";
      return;
    }
    setSelectedFile(file);
  }

  // --- Cleanup polling ---

  useEffect(
    () => () => {
      requestAbortRef.current.abort();
    },
    []
  );

  // --- Upload ---

  async function handleUpload() {
    if (!selectedFile) return;
    const controller = requestAbortRef.current;

    setError(null);
    setStage("uploading");
    setError(null);

    try {
      const result = await api.uploadReceipt(
        roomId,
        token,
        selectedFile,
        undefined,
        controller.signal
      );
      setJobId(result.job_id);

      if (result.parsed_receipt_id) {
        // Synchronous processing — draft is ready
        setParsedReceiptId(result.parsed_receipt_id);
        await loadDraft(result.parsed_receipt_id, controller.signal);
      } else if (result.status === "processing") {
        // Async — need to poll
        setStage("processing");
        void startPolling(result.job_id);
      } else if (result.status === "failed") {
        setStage("error");
        setError(result.error_message ?? "Receipt reading failed. Try a sharper, well-lit photo.");
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      setStage("error");
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  // --- Poll for async job completion ---

  async function startPolling(activeJobId: string) {
    const controller = requestAbortRef.current;
    const deadline = setTimeout(() => {
      controller.abort();
      if (requestAbortRef.current === controller) {
        setStage("error");
        setError("Receipt reading took too long. Check your connection, then try again.");
      }
    }, 90_000);
    try {
      while (!controller.signal.aborted) {
        try {
          const job = await api.getOcrJob(roomId, token, activeJobId, controller.signal);
          if (job.status === "succeeded" && job.parsed_receipt_id) {
            setParsedReceiptId(job.parsed_receipt_id);
          await loadDraft(job.parsed_receipt_id, controller.signal);
            return;
          } else if (job.status === "failed") {
            setStage("error");
            setError(job.error_message ?? "OCR processing failed.");
            return;
          }
        } catch {
          if (controller.signal.aborted) return;
          setStage("error");
          setError("Lost connection while waiting for OCR results.");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, OCR_POLL_INTERVAL_MS));
      }
    } finally {
      clearTimeout(deadline);
    }
  }

  // --- Load parsed draft ---

  async function loadDraft(id: string, signal: AbortSignal = requestAbortRef.current.signal) {
    try {
      const draft = await api.getParsedReceipt(roomId, token, id, signal);
      setServerDraft(draft);
      setLines(draft.items.map(apiToLine));
      setAdjustments(draft.adjustments.map(adjustmentToDraft));
      setMerchantName(draft.merchant_name ?? "");
      setSubtotalAmount(draft.subtotal_paise == null ? "" : (draft.subtotal_paise / 100).toFixed(2));
      setReceiptTotalAmount(draft.total_paise == null ? "" : (draft.total_paise / 100).toFixed(2));
      setAcceptDifference(false);
      setDraftWarnings(draft.warnings);
      setRawText(null);
      setShowRawText(false);
      setStage("draft");
    } catch (err) {
      if (signal.aborted) return;
      setStage("error");
      setError(err instanceof Error ? err.message : "Could not load OCR draft.");
    }
  }

  // --- Debug: load raw text ---

  async function handleLoadRawText() {
    if (!parsedReceiptId || rawText !== null) {
      setShowRawText(!showRawText);
      return;
    }
    setLoadingRawText(true);
    const signal = requestAbortRef.current.signal;
    try {
      const draft = await api.getParsedReceiptDebug(
        roomId,
        token,
        parsedReceiptId,
        signal
      );
      setRawText(draft.redacted_raw_text);
      setShowRawText(true);
    } catch {
      if (signal.aborted) return;
      setRawText("(Could not load raw text)");
      setShowRawText(true);
    } finally {
      setLoadingRawText(false);
    }
  }

  // --- Local line editing ---

  function updateLine(key: string, field: keyof Pick<DraftLine, "name" | "quantity" | "amount">, value: string) {
    setAcceptDifference(false);
    setLines((prev) => prev.map((line) => (line.key === key ? { ...line, [field]: value } : line)));
  }

  function removeLine(key: string) {
    setAcceptDifference(false);
    setLines((prev) => prev.filter((line) => line.key !== key));
  }

  function addLine() {
    setAcceptDifference(false);
    setLines((prev) => [...prev, newBlankLine()]);
  }

  function updateAdjustment(
    key: string,
    field: "type" | "label" | "amount",
    value: string
  ) {
    setAcceptDifference(false);
    setAdjustments((previous) => previous.map((adjustment) => {
      if (adjustment.key !== key) return adjustment;
      if (field === "amount") {
        try {
          return { ...adjustment, amount: value, amount_paise: signedRupeesToPaise(value) };
        } catch {
          return { ...adjustment, amount: value };
        }
      }
      return { ...adjustment, [field]: value };
    }));
  }

  function removeAdjustment(key: string) {
    setAcceptDifference(false);
    setAdjustments((previous) => previous.filter((adjustment) => adjustment.key !== key));
  }

  function addAdjustment() {
    setAcceptDifference(false);
    setAdjustments((previous) => [
      ...previous,
      {
        type: "tax",
        label: "Tax",
        amount_paise: 0,
        allocation_method: "proportional",
        key: crypto.randomUUID(),
        amount: "0.00"
      }
    ]);
  }

  function setExpectedSubtotal(value: string) {
    setAcceptDifference(false);
    setSubtotalAmount(value);
  }

  function setExpectedTotal(value: string) {
    setAcceptDifference(false);
    setReceiptTotalAmount(value);
  }

  const reviewedSubtotal = lines.reduce((sum, line) => {
    try { return sum + lineToApi(line)!.total_paise; } catch { return sum; }
  }, 0);
  const reviewedTotal = reviewedSubtotal + adjustments.reduce((sum, adjustment) => {
    try {
      const signed = signedRupeesToPaise(adjustment.amount);
      return sum + effectiveAdjustmentAmount({ ...adjustment, amount_paise: signed });
    } catch { return sum; }
  }, 0);
  let expectedTotalPaise: number | null = null;
  try { if (receiptTotalAmount.trim()) expectedTotalPaise = parseRupeesToPaise(receiptTotalAmount); } catch { /* Show validation on confirm. */ }
  const totalDifference = expectedTotalPaise == null ? null : reviewedTotal - expectedTotalPaise;
  const hasDiscrepancy = totalDifference == null || totalDifference !== 0;

  // --- Validate local draft ---

  function validateDraft(): {
    items: ParsedReceiptLine[];
    adjustments: ParsedReceiptAdjustment[];
    subtotal_paise: number | null;
    total_paise: number | null;
    errors: string[];
  } {
    const errors: string[] = [];
    const items: ParsedReceiptLine[] = [];
    const apiAdjustments: ParsedReceiptAdjustment[] = [];

    if (lines.length === 0) {
      errors.push("Add at least one item.");
      return { items, adjustments: apiAdjustments, subtotal_paise: null, total_paise: null, errors };
    }

    for (let i = 0; i < lines.length; i++) {
      const parsed = lineToApi(lines[i]);
      if (!parsed) {
        errors.push(`Item ${i + 1}: invalid name, quantity, or amount.`);
      } else {
        items.push(parsed);
      }
    }

    for (const [index, adjustment] of adjustments.entries()) {
      const label = adjustment.label.trim();
      try {
        const amount_paise = signedRupeesToPaise(adjustment.amount);
        if (!label || Math.abs(amount_paise) > 10_000_000) throw new Error();
        apiAdjustments.push({
          type: adjustment.type,
          label,
          amount_paise,
          allocation_method: adjustment.allocation_method
        });
      } catch {
        errors.push(`Adjustment ${index + 1}: enter a valid label and amount.`);
      }
    }

    let subtotal_paise: number | null = null;
    let total_paise: number | null = null;
    try { if (subtotalAmount.trim()) subtotal_paise = parseRupeesToPaise(subtotalAmount); }
    catch { errors.push("Enter a valid receipt subtotal."); }
    try { if (receiptTotalAmount.trim()) total_paise = parseRupeesToPaise(receiptTotalAmount); }
    catch { errors.push("Enter a valid receipt total."); }

    return { items, adjustments: apiAdjustments, subtotal_paise, total_paise, errors };
  }

  // --- Save draft (PATCH) ---

  async function handleSaveDraft() {
    if (!parsedReceiptId) return;
    const signal = requestAbortRef.current.signal;

    const { items, adjustments: apiAdjustments, subtotal_paise, total_paise, errors } = validateDraft();
    if (errors.length > 0) {
      setError(errors.join(" "));
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateParsedReceipt(roomId, token, parsedReceiptId, {
        merchant_name: merchantName.trim() || null,
        items,
        adjustments: apiAdjustments,
        subtotal_paise,
        tax_paise: adjustmentSum(apiAdjustments, "tax"),
        discount_paise: adjustmentSum(apiAdjustments, "discount"),
        total_paise,
        review_fingerprint: serverDraft?.review_fingerprint
      }, signal);
      setServerDraft(updated);
      setLines(updated.items.map(apiToLine));
      setAdjustments(updated.adjustments.map(adjustmentToDraft));
      setMerchantName(updated.merchant_name ?? "");
      setSubtotalAmount(updated.subtotal_paise == null ? "" : (updated.subtotal_paise / 100).toFixed(2));
      setReceiptTotalAmount(updated.total_paise == null ? "" : (updated.total_paise / 100).toFixed(2));
      setDraftWarnings(updated.warnings);
      setAcceptDifference(false);
    } catch (err) {
      if (signal.aborted) return;
      setError(err instanceof Error ? err.message : "Could not save draft.");
    } finally {
      setSaving(false);
    }
  }

  // --- Confirm: validate → PATCH → POST confirm → refresh ---

  async function handleConfirm() {
    if (!parsedReceiptId) return;
    const signal = requestAbortRef.current.signal;

    const { items, adjustments: apiAdjustments, subtotal_paise, total_paise, errors } = validateDraft();
    if (errors.length > 0) {
      setError(errors.join(" "));
      return;
    }

    setStage("confirming");
    setError(null);

    let confirmStarted = false;
    try {
      // 1. PATCH latest local draft
      const updated = await api.updateParsedReceipt(roomId, token, parsedReceiptId, {
        merchant_name: merchantName.trim() || null,
        items,
        adjustments: apiAdjustments,
        subtotal_paise,
        tax_paise: adjustmentSum(apiAdjustments, "tax"),
        discount_paise: adjustmentSum(apiAdjustments, "discount"),
        total_paise,
        review_fingerprint: serverDraft?.review_fingerprint
      }, signal);

      // 2. POST confirm
      confirmStarted = true;
      const result = await api.confirmParsedReceipt(roomId, token, parsedReceiptId, {
        accept_unreconciled_total: acceptDifference,
        review_fingerprint: updated.review_fingerprint
      }, signal);
      setConfirmedCount(result.created_item_ids.length);
      setStage("confirmed");

      // 3. Refresh parent room
      try {
        await onConfirmed();
      } catch {
        setError("Receipt added; refresh needed.");
      }
    } catch (err) {
      const status = typeof err === "object" && err !== null && "status" in err
        ? (err as { status?: number }).status
        : undefined;
      const uncertain = confirmStarted && status == null;
      if (signal.aborted) return;
      if (uncertain) {
        setStage("error");
        setError("We couldn't verify whether the receipt was added. Reload the bill before trying again.");
        return;
      }
      setStage("draft");
      setError(err instanceof Error ? err.message : "Could not confirm receipt.");
    }
  }

  // --- Reset to idle ---

  function handleReset() {
    requestAbortRef.current.abort();
    requestAbortRef.current = new AbortController();
    setStage("idle");
    setError(null);
    setFileError(null);
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setJobId(null);
    setParsedReceiptId(null);
    setServerDraft(null);
    setLines([]);
    setAdjustments([]);
    setMerchantName("");
    setSubtotalAmount("");
    setReceiptTotalAmount("");
    setAcceptDifference(false);
    setDraftWarnings([]);
    setRawText(null);
    setShowRawText(false);
    setConfirmedCount(0);
    setSaving(false);
  }

  // --- Render ---

  return (
    <section id="receipt-upload" className="rs-receipt-panel rounded-md border border-border bg-surface p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">
            <Camera size={18} className="mr-1.5 inline-block align-text-bottom" aria-hidden="true" />
            Scan Receipt
          </h2>
          <p className="mt-1 text-sm text-muted">
            OCR can make mistakes. Review item names and amounts before adding them.
          </p>
        </div>
        {stage !== "idle" && stage !== "confirmed" ? (
          <Button type="button" variant="ghost" onClick={handleReset}>
            <RotateCcw size={14} aria-hidden="true" />
            Reset
          </Button>
        ) : null}
      </div>

      {/* Error banner */}
      {(error || fileError) && (
        <div className="mt-3 rounded-md bg-danger-soft px-3 py-2 text-sm font-medium text-coral">
          {fileError ?? error}
        </div>
      )}

      {/* Idle: file picker */}
      {stage === "idle" && (
        <div className="mt-3 grid gap-3">
          <label
            className="rs-receipt-picker flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-border-strong bg-cloud p-4 text-sm text-muted transition hover:border-leaf hover:bg-mint/40"
            htmlFor="receipt-file-input"
          >
            <Upload size={24} aria-hidden="true" />
            {selectedFile ? (
              <span className="font-semibold text-ink">{selectedFile.name}</span>
            ) : (
              <span>Tap to select a receipt image (PNG or JPEG, max 5 MiB)</span>
            )}
          </label>
        <input
          ref={fileInputRef}
          id="receipt-file-input"
            type="file"
            accept="image/png,image/jpeg"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button type="button" disabled={!selectedFile} onClick={handleUpload}>
            <Camera size={16} aria-hidden="true" />
            Scan receipt
          </Button>
        </div>
      )}

      {/* Uploading */}
      {stage === "uploading" && (
        <div className="mt-4 flex items-center gap-3 text-sm text-muted">
          <Loader2 size={18} className="animate-spin" aria-hidden="true" />
          Uploading receipt image…
        </div>
      )}

      {/* Processing */}
      {stage === "processing" && (
        <div className="mt-4 flex items-center gap-3 text-sm text-muted">
          <Loader2 size={18} className="animate-spin" aria-hidden="true" />
          Processing OCR… This may take a few seconds.
        </div>
      )}

      {/* Error with retry */}
      {stage === "error" && (
        <div className="mt-3 grid gap-3">
          <Button type="button" variant="secondary" onClick={handleReset}>
            <RotateCcw size={16} aria-hidden="true" />
            Try again
          </Button>
        </div>
      )}

      {/* Draft review */}
      {stage === "draft" && serverDraft && (
        <div className="mt-3 grid gap-3" data-testid="ocr-draft-review">
          {/* Warnings */}
          {(serverDraft.needs_review || hasDiscrepancy) && (
            <div className="flex items-center gap-2 rounded-md bg-warning-soft px-3 py-2 text-sm font-medium text-amber">
              <AlertTriangle size={16} aria-hidden="true" />
              Review the items, taxes, and charges before adding them
            </div>
          )}
          {draftWarnings.length > 0 && (
            <ul className="rounded-md bg-warning-soft px-3 py-2 text-xs text-muted">
              {draftWarnings.map((warning, index) => (
                <li key={index}>⚠ {WARNING_LABELS[warning] ?? "A receipt detail needs checking."}</li>
              ))}
            </ul>
          )}

          {/* Merchant */}
          <Input
            label="Merchant"
            value={merchantName}
            onChange={(e) => { setAcceptDifference(false); setMerchantName(e.target.value); }}
            placeholder="Restaurant name (optional)"
          />

          {/* Items */}
          <div className="grid gap-2">
            <p className="text-sm font-semibold text-muted">Items ({lines.length})</p>
            {lines.map((line, index) => (
              <div key={line.key} className="grid grid-cols-[1fr_60px_90px_36px] items-end gap-2">
                <Input
                  label={index === 0 ? "Name" : ""}
                  value={line.name}
                  onChange={(e) => updateLine(line.key, "name", e.target.value)}
                  placeholder="Item name"
                />
                <Input
                  label={index === 0 ? "Qty" : ""}
                  inputMode="numeric"
                  value={line.quantity}
                  onChange={(e) => updateLine(line.key, "quantity", e.target.value)}
                />
                <Input
                  label={index === 0 ? "₹" : ""}
                  inputMode="decimal"
                  value={line.amount}
                  onChange={(e) => updateLine(line.key, "amount", e.target.value)}
                />
                <button
                  type="button"
                  className="mb-0.5 inline-flex min-h-11 items-center justify-center rounded-md text-coral transition hover:bg-coral/10"
                  onClick={() => removeLine(line.key)}
                  aria-label={`Delete item ${index + 1}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            <Button type="button" variant="ghost" onClick={addLine}>
              <Plus size={16} aria-hidden="true" />
              Add item
            </Button>
          </div>

          {/* Editable taxes, charges, discount, and rounding */}
          <div className="grid gap-2" data-testid="ocr-adjustments">
            <p className="text-sm font-semibold text-muted">Taxes and adjustments</p>
            {adjustments.map((adjustment, index) => (
              <div key={adjustment.key} className="grid grid-cols-[1fr_1fr_90px_36px] items-end gap-2">
                <Input
                  label={index === 0 ? "Label" : ""}
                  value={adjustment.label}
                  onChange={(event) => updateAdjustment(adjustment.key, "label", event.target.value)}
                  placeholder="Adjustment label"
                />
                <label className="grid gap-1 text-xs font-medium text-muted">
                  {index === 0 ? "Type" : ""}
                  <select
                    aria-label={`Adjustment type ${index + 1}`}
                    className="min-h-11 rounded-md border border-border bg-surface px-2 text-sm text-ink"
                    value={adjustment.type}
                    onChange={(event) => updateAdjustment(adjustment.key, "type", event.target.value)}
                  >
                    {ADJUSTMENT_TYPES.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
                  </select>
                </label>
                <Input
                  label={index === 0 ? "₹" : ""}
                  inputMode="decimal"
                  value={adjustment.amount}
                  onChange={(event) => updateAdjustment(adjustment.key, "amount", event.target.value)}
                />
                <button
                  type="button"
                  className="mb-0.5 inline-flex min-h-11 items-center justify-center rounded-md text-coral transition hover:bg-coral/10"
                  onClick={() => removeAdjustment(adjustment.key)}
                  aria-label={`Delete adjustment ${index + 1}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            <Button type="button" variant="ghost" onClick={addAdjustment}>
              <Plus size={16} aria-hidden="true" />
              Add tax or adjustment
            </Button>
          </div>

          {/* Reconciled totals */}
          <div className="grid gap-2 rounded-md bg-cloud p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted">Reviewed items subtotal</span>
              <strong>{formatPaise(reviewedSubtotal)}</strong>
            </div>
            {adjustments.map((adjustment) => {
              let amount = 0;
              try { amount = signedRupeesToPaise(adjustment.amount); } catch { /* The row remains editable. */ }
              return (
                <div key={`summary-${adjustment.key}`} className="flex items-center justify-between">
                  <span className="text-muted">{adjustment.label || "Adjustment"}</span>
                  <strong>{formatPaise(effectiveAdjustmentAmount({ ...adjustment, amount_paise: amount }))}</strong>
                </div>
              );
            })}
            <div className="flex items-center justify-between border-t border-border pt-2">
              <span>Calculated bill total</span>
              <strong>{formatPaise(reviewedTotal)}</strong>
            </div>
            <div className="grid gap-2 border-t border-border pt-2 sm:grid-cols-2">
              <Input
                label="Receipt subtotal"
                inputMode="decimal"
                value={subtotalAmount}
                onChange={(event) => setExpectedSubtotal(event.target.value)}
                placeholder="Not read"
              />
              <Input
                label="Receipt total"
                inputMode="decimal"
                value={receiptTotalAmount}
                onChange={(event) => setExpectedTotal(event.target.value)}
                placeholder="Not read"
              />
            </div>
          </div>

          {hasDiscrepancy && (
            <div className="grid gap-2 rounded-md border border-amber bg-warning-soft p-3 text-sm">
              <p>
                {expectedTotalPaise == null
                  ? "Receipt total is missing."
                  : `Calculated ${formatPaise(reviewedTotal)}; receipt total ${formatPaise(expectedTotalPaise)}; difference ${formatPaise(totalDifference ?? 0)}.`}
              </p>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  aria-label="Use the reviewed bill total despite this difference."
                  checked={acceptDifference}
                  onChange={(event) => setAcceptDifference(event.target.checked)}
                  className="mt-1"
                />
                <span>Use the reviewed bill total despite this difference.</span>
              </label>
            </div>
          )}

          {/* Raw text debug (collapsed, explicit action) */}
          <details open={showRawText} className="text-xs">
            <summary
              className="flex cursor-pointer items-center gap-1 text-muted select-none"
              onClick={(e) => {
                e.preventDefault();
                void handleLoadRawText();
              }}
            >
              {showRawText ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {loadingRawText ? "Loading raw OCR text…" : "Raw OCR text (debug)"}
            </summary>
            {showRawText && rawText !== null && (
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-cloud p-2 text-[10px] text-muted">
                {rawText}
              </pre>
            )}
          </details>

          {/* Actions */}
          <div className="grid grid-cols-2 gap-3">
            <Button type="button" variant="secondary" disabled={saving} onClick={handleSaveDraft}>
              {saving ? <Loader2 size={14} className="animate-spin" /> : null}
              Save draft
            </Button>
            <Button type="button" disabled={saving || (hasDiscrepancy && !acceptDifference)} onClick={handleConfirm}>
              <Check size={16} aria-hidden="true" />
              Confirm into room
            </Button>
          </div>
        </div>
      )}

      {/* Confirming */}
      {stage === "confirming" && (
        <div className="mt-4 flex items-center gap-3 text-sm text-muted">
          <Loader2 size={18} className="animate-spin" aria-hidden="true" />
          Confirming receipt items…
        </div>
      )}

      {/* Confirmed */}
      {stage === "confirmed" && (
        <div className="mt-3 grid gap-3">
          <div className="flex items-center gap-2 rounded-md bg-mint px-3 py-2 text-sm font-medium">
            <Check size={16} className="text-leaf" aria-hidden="true" />
            {confirmedCount} item{confirmedCount !== 1 ? "s" : ""} added to room from receipt.
          </div>
          <Button type="button" variant="secondary" onClick={handleReset}>
            <Camera size={16} aria-hidden="true" />
            Scan another receipt
          </Button>
        </div>
      )}
    </section>
  );
}
