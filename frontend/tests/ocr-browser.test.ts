import { afterEach, describe, expect, it, vi } from "vitest";

const paddle = vi.hoisted(() => ({
  create: vi.fn()
}));

vi.mock("@paddleocr/paddleocr-js", () => ({ PaddleOCR: paddle }));

import { runBrowserReceiptOcr } from "@/lib/ocr/browser";

describe("browser receipt OCR adapter", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("runs the worker-backed reader and normalizes its candidate", async () => {
    const dispose = vi.fn().mockResolvedValue(undefined);
    const predict = vi.fn().mockResolvedValue([
      {
        items: [
          {
            poly: [
              [20, 40],
              [120, 40],
              [120, 60],
              [20, 60]
            ],
            text: "Tea 120.00",
            score: 0.97
          }
        ]
      }
    ]);
    paddle.create.mockResolvedValue({ dispose, predict });
    const progress: string[] = [];

    const result = await runBrowserReceiptOcr(
      new File(["receipt"], "receipt.png", { type: "image/png" }),
      { onProgress: (value) => progress.push(value) }
    );

    expect(progress).toEqual(["loading-model", "reading"]);
    expect(paddle.create).toHaveBeenCalledWith({
      lang: "en",
      ocrVersion: "PP-OCRv5",
      worker: true,
      ortOptions: {
        backend: "wasm",
        numThreads: 1,
        simd: true
      }
    });
    expect(predict).toHaveBeenCalledTimes(1);
    expect(result.raw_text).toBe("Tea 120.00");
    expect(result.lines[0].poly).toEqual([
      { x: 20, y: 40 },
      { x: 120, y: 40 },
      { x: 120, y: 60 },
      { x: 20, y: 60 }
    ]);
    expect(dispose).toHaveBeenCalledTimes(1);
  });

  it("disposes the OCR worker when the result is invalid", async () => {
    const dispose = vi.fn().mockResolvedValue(undefined);
    paddle.create.mockResolvedValue({
      dispose,
      predict: vi.fn().mockResolvedValue([{ items: [] }])
    });

    await expect(
      runBrowserReceiptOcr(new File(["receipt"], "receipt.png", { type: "image/png" }))
    ).rejects.toThrow("unusable amount of text");
    expect(dispose).toHaveBeenCalledTimes(1);
  });
});
