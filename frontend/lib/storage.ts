export type CreatorSession = {
  roomId: string;
  role: "creator";
  token: string;
  inviteToken: string;
  lastSequence: number;
};

export type ParticipantSession = {
  roomId: string;
  role: "participant";
  token: string;
  participantId: string;
  nickname: string;
  lastSequence: number;
};

const creatorKey = (roomId: string) => `receiptsplit:creator:${roomId}`;
const participantKey = (roomId: string) => `receiptsplit:participant:${roomId}`;

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, JSON.stringify(value));
}

export function saveCreatorSession(session: CreatorSession): void {
  writeJson(creatorKey(session.roomId), session);
}

export function getCreatorSession(roomId: string): CreatorSession | null {
  return readJson<CreatorSession>(creatorKey(roomId));
}

export function saveParticipantSession(session: ParticipantSession): void {
  writeJson(participantKey(session.roomId), session);
}

export function getParticipantSession(roomId: string): ParticipantSession | null {
  return readJson<ParticipantSession>(participantKey(roomId));
}

export function updateLastSequence(
  roomId: string,
  role: "creator" | "participant",
  sequence: number
): void {
  if (role === "creator") {
    const session = getCreatorSession(roomId);
    if (session) {
      saveCreatorSession({ ...session, lastSequence: sequence });
    }
    return;
  }

  const session = getParticipantSession(roomId);
  if (session) {
    saveParticipantSession({ ...session, lastSequence: sequence });
  }
}
