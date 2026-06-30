import { describe, expect, it } from "vitest";

import { parseApiError } from "@/lib/api";

describe("API error parser", () => {
  it("parses backend domain error shape", async () => {
    const response = new Response(
      JSON.stringify({
        error: { code: "VERSION_CONFLICT", message: "Version conflict" }
      }),
      { status: 409 }
    );

    const error = await parseApiError(response);

    expect(error.status).toBe(409);
    expect(error.code).toBe("VERSION_CONFLICT");
    expect(error.message).toBe("Version conflict");
  });

  it("falls back to HTTP status text", async () => {
    const error = await parseApiError(new Response("", { status: 403, statusText: "Forbidden" }));

    expect(error.status).toBe(403);
    expect(error.code).toBe("HTTP_403");
    expect(error.message).toBe("Forbidden");
  });
});
