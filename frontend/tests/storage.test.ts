import { beforeEach, describe, expect, it } from "vitest";

import {
  getCreatorSession,
  getParticipantSession,
  saveCreatorSession,
  saveParticipantSession
} from "@/lib/storage";

describe("session storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves creator token sessions", () => {
    saveCreatorSession({
      roomId: "room-1",
      role: "creator",
      token: "rs_cr_token",
      inviteToken: "rs_inv_token",
      lastSequence: 7
    });

    expect(getCreatorSession("room-1")).toEqual({
      roomId: "room-1",
      role: "creator",
      token: "rs_cr_token",
      inviteToken: "rs_inv_token",
      lastSequence: 7
    });
  });

  it("stores and retrieves participant token sessions", () => {
    saveParticipantSession({
      roomId: "room-1",
      role: "participant",
      token: "rs_pt_token",
      participantId: "participant-1",
      nickname: "AJ",
      lastSequence: 3
    });

    expect(getParticipantSession("room-1")).toEqual({
      roomId: "room-1",
      role: "participant",
      token: "rs_pt_token",
      participantId: "participant-1",
      nickname: "AJ",
      lastSequence: 3
    });
  });
});
