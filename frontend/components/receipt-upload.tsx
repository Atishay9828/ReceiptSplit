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
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatPaise, parseRupeesToPaise } from "@/lib/money";
import type {
  ParsedReceiptDraftResponse,
  ParsedReceiptLine
} from "@/types/api";

// --- Constants ---

const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg", "image/jpg"]);
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB conservative frontend limit
const OCR_POLL_INTERVAL_MS = 2000;

type OcrStage = "idle" | "uploading" | "processing" | "draft" | "confirming" | "confirmed" | "error";

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
  confidence: number;
};

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
    unit_price_paise: qty > 1 ? Math.floor(totalPaise / qty) : null,
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
    confidence: item.confidence
  };
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) {
    return "Only PNG and JPEG images are supported.";
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 10 MB.`;
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
    confidence: 1.0
  };
}

// --- Component ---

export function ReceiptUpload({ roomId, token, onConfirmed }: ReceiptUploadProps) {
  const [stage, setStage] = useState<OcrStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // OCR tracking
  const [, setJobId] = useState<string | null>(null);
  const [parsedReceiptId, setParsedReceiptId] = useState<string | null>(null);
  const [serverDraft, setServerDraft] = useState<ParsedReceiptDraftResponse | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Local editable draft state
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [merchantName, setMerchantName] = useState("");
  const [draftWarnings, setDraftWarnings] = useState<string[]>([]);
  const [needsReview, setNeedsReview] = useState(false);
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

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => clearPoll, [clearPoll]);

  // --- Upload ---

  async function handleUpload() {
    if (!selectedFile) return;

    setStage("uploading");
    setError(null);

    try {
      const result = await api.uploadReceipt(roomId, token, selectedFile);
      setJobId(result.job_id);

      if (result.parsed_receipt_id) {
        // Synchronous processing — draft is ready
        setParsedReceiptId(result.parsed_receipt_id);
        await loadDraft(result.parsed_receipt_id);
      } else if (result.status === "processing") {
        // Async — need to poll
        setStage("processing");
        startPolling(result.job_id);
      } else if (result.status === "failed") {
        setStage("error");
        setError("OCR processing failed. Try re-uploading.");
      }
    } catch (err) {
      setStage("error");
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  // --- Poll for async job completion ---

  function startPolling(activeJobId: string) {
    clearPoll();
    pollRef.current = setInterval(async () => {
      try {
        const job = await api.getOcrJob(roomId, token, activeJobId);
        if (job.status === "succeeded" && job.parsed_receipt_id) {
          clearPoll();
          setParsedReceiptId(job.parsed_receipt_id);
          await loadDraft(job.parsed_receipt_id);
        } else if (job.status === "failed") {
          clearPoll();
          setStage("error");
          setError(job.error_message ?? "OCR processing failed.");
        }
        // still processing → keep polling
      } catch {
        clearPoll();
        setStage("error");
        setError("Lost connection while waiting for OCR results.");
      }
    }, OCR_POLL_INTERVAL_MS);
  }

  // --- Load parsed draft ---

  async function loadDraft(id: string) {
    try {
      const draft = await api.getParsedReceipt(roomId, token, id);
      setServerDraft(draft);
      setLines(draft.items.map(apiToLine));
      setMerchantName(draft.merchant_name ?? "");
      setDraftWarnings(draft.warnings);
      setNeedsReview(draft.needs_review);
      setRawText(null);
      setShowRawText(false);
      setStage("draft");
    } catch (err) {
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
    try {
      const draft = await api.getParsedReceiptDebug(roomId, token, parsedReceiptId);
      setRawText(draft.redacted_raw_text);
      setShowRawText(true);
    } catch {
      setRawText("(Could not load raw text)");
      setShowRawText(true);
    } finally {
      setLoadingRawText(false);
    }
  }

  // --- Local line editing ---

  function updateLine(key: string, field: keyof Pick<DraftLine, "name" | "quantity" | "amount">, value: string) {
    setLines((prev) => prev.map((line) => (line.key === key ? { ...line, [field]: value } : line)));
  }

  function removeLine(key: string) {
    setLines((prev) => prev.filter((line) => line.key !== key));
  }

  function addLine() {
    setLines((prev) => [...prev, newBlankLine()]);
  }

  // --- Validate local draft ---

  function validateDraft(): { items: ParsedReceiptLine[]; errors: string[] } {
    const errors: string[] = [];
    const items: ParsedReceiptLine[] = [];

    if (lines.length === 0) {
      errors.push("Add at least one item.");
      return { items, errors };
    }

    for (let i = 0; i < lines.length; i++) {
      const parsed = lineToApi(lines[i]);
      if (!parsed) {
        errors.push(`Item ${i + 1}: invalid name, quantity, or amount.`);
      } else {
        items.push(parsed);
      }
    }

    return { items, errors };
  }

  // --- Save draft (PATCH) ---

  async function handleSaveDraft() {
    if (!parsedReceiptId) return;

    const { items, errors } = validateDraft();
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
        needs_review: needsReview,
        warnings: draftWarnings
      });
      setServerDraft(updated);
      setLines(updated.items.map(apiToLine));
      setMerchantName(updated.merchant_name ?? "");
      setDraftWarnings(updated.warnings);
      setNeedsReview(updated.needs_review);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save draft.");
    } finally {
      setSaving(false);
    }
  }

  // --- Confirm: validate → PATCH → POST confirm → refresh ---

  async function handleConfirm() {
    if (!parsedReceiptId) return;

    const { items, errors } = validateDraft();
    if (errors.length > 0) {
      setError(errors.join(" "));
      return;
    }

    setStage("confirming");
    setError(null);

    try {
      // 1. PATCH latest local draft
      await api.updateParsedReceipt(roomId, token, parsedReceiptId, {
        merchant_name: merchantName.trim() || null,
        items,
        needs_review: false,
        warnings: draftWarnings
      });

      // 2. POST confirm
      const result = await api.confirmParsedReceipt(roomId, token, parsedReceiptId);
      setConfirmedCount(result.created_item_ids.length);
      setStage("confirmed");

      // 3. Refresh parent room
      await onConfirmed();
    } catch (err) {
      setStage("draft");
      setError(err instanceof Error ? err.message : "Could not confirm receipt.");
    }
  }

  // --- Reset to idle ---

  function handleReset() {
    clearPoll();
    setStage("idle");
    setError(null);
    setFileError(null);
    setSelectedFile(null);
    setJobId(null);
    setParsedReceiptId(null);
    setServerDraft(null);
    setLines([]);
    setMerchantName("");
    setDraftWarnings([]);
    setNeedsReview(false);
    setRawText(null);
    setShowRawText(false);
    setConfirmedCount(0);
  }

  // --- Render ---

  return (
    <section id="receipt-upload" className="rounded-md bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold">
          <Camera size={18} className="mr-1.5 inline-block align-text-bottom" aria-hidden="true" />
          Scan Receipt
        </h2>
        {stage !== "idle" && stage !== "confirmed" ? (
          <Button type="button" variant="ghost" onClick={handleReset}>
            <RotateCcw size={14} aria-hidden="true" />
            Reset
          </Button>
        ) : null}
      </div>

      {/* Error banner */}
      {(error || fileError) && (
        <div className="mt-3 rounded-md bg-coral/10 px-3 py-2 text-sm font-medium text-coral">
          {fileError ?? error}
        </div>
      )}

      {/* Idle: file picker */}
      {stage === "idle" && (
        <div className="mt-3 grid gap-3">
          <label
            className="flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-[#ccd8d1] bg-cloud p-4 text-sm text-[#63706b] transition hover:border-leaf hover:bg-mint/40"
            htmlFor="receipt-file-input"
          >
            <Upload size={24} aria-hidden="true" />
            {selectedFile ? (
              <span className="font-semibold text-ink">{selectedFile.name}</span>
            ) : (
              <span>Tap to select a receipt image (PNG or JPEG, max 10 MB)</span>
            )}
          </label>
          <input
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
        <div className="mt-4 flex items-center gap-3 text-sm text-[#63706b]">
          <Loader2 size={18} className="animate-spin" aria-hidden="true" />
          Uploading receipt image…
        </div>
      )}

      {/* Processing */}
      {stage === "processing" && (
        <div className="mt-4 flex items-center gap-3 text-sm text-[#63706b]">
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
          {needsReview && (
            <div className="flex items-center gap-2 rounded-md bg-amber/15 px-3 py-2 text-sm font-medium text-amber-800">
              <AlertTriangle size={16} aria-hidden="true" />
              Needs review — check items below
            </div>
          )}
          {draftWarnings.length > 0 && (
            <ul className="rounded-md bg-amber/10 px-3 py-2 text-xs text-[#63706b]">
              {draftWarnings.map((warning, index) => (
                <li key={index}>⚠ {warning}</li>
              ))}
            </ul>
          )}

          {/* Merchant */}
          <Input
            label="Merchant"
            value={merchantName}
            onChange={(e) => setMerchantName(e.target.value)}
            placeholder="Restaurant name (optional)"
          />

          {/* Items */}
          <div className="grid gap-2">
            <p className="text-sm font-semibold text-[#63706b]">Items ({lines.length})</p>
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

          {/* Summary */}
          {serverDraft.total_paise != null && (
            <div className="flex items-center justify-between rounded-md bg-cloud px-3 py-2 text-sm">
              <span className="text-[#63706b]">OCR total</span>
              <strong>{formatPaise(serverDraft.total_paise)}</strong>
            </div>
          )}

          {/* Confidence */}
          <div className="flex items-center justify-between text-xs text-[#63706b]">
            <span>Confidence: {(serverDraft.confidence * 100).toFixed(0)}%</span>
            <span>Parser: {serverDraft.parser_version}</span>
          </div>

          {/* Raw text debug (collapsed, explicit action) */}
          <details open={showRawText} className="text-xs">
            <summary
              className="flex cursor-pointer items-center gap-1 text-[#63706b] select-none"
              onClick={(e) => {
                e.preventDefault();
                void handleLoadRawText();
              }}
            >
              {showRawText ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {loadingRawText ? "Loading raw OCR text…" : "Raw OCR text (debug)"}
            </summary>
            {showRawText && rawText !== null && (
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-cloud p-2 text-[10px] text-[#63706b]">
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
            <Button type="button" onClick={handleConfirm}>
              <Check size={16} aria-hidden="true" />
              Confirm into room
            </Button>
          </div>
        </div>
      )}

      {/* Confirming */}
      {stage === "confirming" && (
        <div className="mt-4 flex items-center gap-3 text-sm text-[#63706b]">
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
