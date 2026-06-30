"use client";

import { useParams } from "next/navigation";

import { RoomClient } from "@/components/room-client";

export default function ParticipantRoomPage() {
  const params = useParams<{ roomId: string }>();
  return <RoomClient roomId={params.roomId} mode="participant" />;
}
