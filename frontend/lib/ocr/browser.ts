import type {
  BrowserOcrCandidate,
  BrowserOcrCandidateLine
} from "@/types/api";
import type { OcrResult, PaddleOCR } from "@paddleocr/paddleocr-js";

const MAX_OCR_LINES = 2000;
const MAX_LINE_TEXT_LENGTH = 1000;
const MAX_OCR_TEXT_LENGTH = 100_000;
const MAX_COORDINATE = 5000;

export type BrowserOcrProgress = "loading-model" | "reading";

export function isBrowserReceiptOcrEnabled(): boolean {
  return process.env.NEXT_PUBLIC_RECEIPTSPLIT_BROWSER_OCR === "true";
}

export async function runBrowserReceiptOcr(
  file: File,
  options: {
    signal?: AbortSignal;
    onProgress?: (progress: BrowserOcrProgress) => void;
  } = {}
): Promise<BrowserOcrCandidate> {
  const { signal, onProgress } = options;
  throwIfAborted(signal);
  onProgress?.("loading-model");

  let ocr: Awaited<ReturnType<typeof PaddleOCR.create>> | null = null;
  const onAbort = () => {
    void ocr?.dispose();
  };
  signal?.addEventListener("abort", onAbort, { once: true });

  try {
    const { PaddleOCR } = await import("@paddleocr/paddleocr-js");
    throwIfAborted(signal);
    ocr = await PaddleOCR.create({
      lang: "en",
      ocrVersion: "PP-OCRv5",
      worker: true,
      ortOptions: {
        backend: "wasm",
        numThreads: 1,
        simd: true
      }
    });
    throwIfAborted(signal);
    onProgress?.("reading");
    const [result] = await ocr.predict(file);
    throwIfAborted(signal);
    return candidateFromResult(result);
  } finally {
    signal?.removeEventListener("abort", onAbort);
    if (ocr) {
      try {
        await ocr.dispose();
      } catch {
        // Disposal failure must not expose OCR text or replace the user-facing result.
      }
    }
  }
}

function candidateFromResult(result: OcrResult): BrowserOcrCandidate {
  if (!result || !Array.isArray(result.items)) {
    throw new Error("Browser OCR returned no readable text.");
  }
  if (result.items.length > MAX_OCR_LINES) {
    throw new Error("Browser OCR returned too many text lines.");
  }

  const lines = result.items.map(toCandidateLine);
  const rawText = lines.map((line) => line.text).join("\n").trim();
  if (!rawText || rawText.length > MAX_OCR_TEXT_LENGTH) {
    throw new Error("Browser OCR returned an unusable amount of text.");
  }

  return {
    provider: "paddleocr-js",
    model: "PP-OCRv5",
    language: "en",
    raw_text: rawText,
    lines
  };
}

function toCandidateLine(item: {
  poly: Array<[number, number]>;
  text: string;
  score: number;
}): BrowserOcrCandidateLine {
  const text = item.text.trim();
  if (!text || text.length > MAX_LINE_TEXT_LENGTH || !Number.isFinite(item.score)) {
    throw new Error("Browser OCR returned an invalid text line.");
  }
  if (item.score < 0 || item.score > 1 || item.poly.length < 4) {
    throw new Error("Browser OCR returned invalid confidence or geometry.");
  }

  const points = item.poly.map(([x, y]) => {
    if (
      !Number.isFinite(x) ||
      !Number.isFinite(y) ||
      x < 0 ||
      x > MAX_COORDINATE ||
      y < 0 ||
      y > MAX_COORDINATE
    ) {
      throw new Error("Browser OCR returned invalid geometry.");
    }
    return { x, y };
  });
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const right = Math.max(...xs);
  const bottom = Math.max(...ys);

  return {
    text,
    score: item.score,
    poly: [
      { x: left, y: top },
      { x: right, y: top },
      { x: right, y: bottom },
      { x: left, y: bottom }
    ]
  };
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    const error = new Error("Browser OCR was cancelled.");
    error.name = "AbortError";
    throw error;
  }
}
