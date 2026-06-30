export function encodeInviteParam(roomId: string, inviteToken: string): string {
  return encodeURIComponent(`${roomId}:${inviteToken}`);
}

export function decodeInviteParam(param: string): { roomId: string; inviteToken: string } | null {
  const decoded = decodeURIComponent(param);
  const separator = decoded.indexOf(":");
  if (separator <= 0 || separator === decoded.length - 1) {
    return null;
  }

  return {
    roomId: decoded.slice(0, separator),
    inviteToken: decoded.slice(separator + 1)
  };
}
