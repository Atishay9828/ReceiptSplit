import { describe, expect, it, vi } from "vitest";

import { RoomEventSync } from "@/lib/events";

describe("event client", () => {
  it("deduplicates sequence numbers and updates last sequence", () => {
    const refetch = vi.fn();
    const sync = new RoomEventSync({ roomId: "room-1", token: "token", onRefetch: refetch });

    sync.handleEvent({ sequence_no: 1, event_type: "item.created" });
    sync.handleEvent({ sequence_no: 1, event_type: "item.created" });
    sync.handleEvent({ sequence_no: 3, event_type: "claim.created" });

    expect(sync.lastSequence).toBe(3);
    expect(refetch).toHaveBeenCalledTimes(2);
  });

  it("uses last sequence when building reconnect URLs", () => {
    const sync = new RoomEventSync({
      roomId: "room-1",
      token: "token",
      apiBaseUrl: "http://localhost:8000",
      initialSequence: 9,
      onRefetch: vi.fn()
    });

    expect(sync.streamUrl()).toBe(
      "http://localhost:8000/api/rooms/room-1/events/stream?after_sequence=9"
    );
  });
});
