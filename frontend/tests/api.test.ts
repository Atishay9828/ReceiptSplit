import { describe, expect, it, vi } from "vitest";

import { ReceiptSplitApi, parseApiError } from "@/lib/api";

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

  it("uses settlement endpoints without sending client-controlled amount", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new ReceiptSplitApi("http://api.test");

    await client.openPayment("room-1", "request-1", "token");
    await client.claimPaid("room-1", "request-1", "token");
    await client.confirmSettlement("room-1", "request-1", "token");
    await client.disputeSettlement("room-1", "request-1", "token", {
      reason: "Could not match payment"
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/api/rooms/room-1/settlement/requests/request-1/open-payment",
      expect.objectContaining({ method: "POST", body: undefined })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api.test/api/rooms/room-1/settlement/requests/request-1/claim-paid",
      expect.objectContaining({ method: "POST", body: undefined })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api.test/api/rooms/room-1/settlement/requests/request-1/confirm",
      expect.objectContaining({ method: "POST", body: undefined })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "http://api.test/api/rooms/room-1/settlement/requests/request-1/dispute",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ reason: "Could not match payment" }) })
    );
  });

  it("submits abuse reports without putting tokens in the request body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "report-1", reason: "wrong_payee", message: "Check VPA" }), {
        status: 201,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = new ReceiptSplitApi("http://api.test");

    await client.reportAbuse("room-1", "rs_pt_secret", {
      reason: "wrong_payee",
      message: "Check VPA"
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/rooms/room-1/abuse-reports",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer rs_pt_secret" }),
        body: JSON.stringify({ reason: "wrong_payee", message: "Check VPA" })
      })
    );
  });
});
