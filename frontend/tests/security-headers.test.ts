import { describe, expect, it } from "vitest";

// @ts-expect-error Next config is an ESM config file without a local TS declaration.
import nextConfig from "../next.config.mjs";

describe("sensitive route headers", () => {
  it("marks join and room pages as noindex with basic security headers", async () => {
    expect(nextConfig.headers).toBeTypeOf("function");
    const headers = await nextConfig.headers();

    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source: "/join/:inviteToken" }),
        expect.objectContaining({ source: "/rooms/:roomId" }),
        expect.objectContaining({ source: "/rooms/:roomId/creator" })
      ])
    );

    for (const route of headers) {
      expect(route.headers).toEqual(
        expect.arrayContaining([
          { key: "X-Robots-Tag", value: "noindex, nofollow" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" }
        ])
      );
    }
  });
});
