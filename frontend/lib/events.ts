import { API_BASE_URL, parseApiError } from "@/lib/api";
import type { RoomEvent } from "@/types/api";

type RoomEventSyncOptions = {
  roomId: string;
  token: string;
  apiBaseUrl?: string;
  initialSequence?: number;
  onRefetch: () => void | Promise<void>;
  onSequence?: (sequence: number) => void;
  onConnectionChange?: (connected: boolean) => void;
};

export class RoomEventSync {
  private seen = new Set<number>();
  private controller: AbortController | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private replayTimer: ReturnType<typeof setInterval> | null = null;
  private replayInFlight: Promise<void> | null = null;
  private readonly baseUrl: string;
  lastSequence: number;

  constructor(private readonly options: RoomEventSyncOptions) {
    this.baseUrl = (options.apiBaseUrl ?? API_BASE_URL).replace(/\/$/, "");
    this.lastSequence = options.initialSequence ?? 0;
  }

  streamUrl(): string {
    return `${this.baseUrl}/api/rooms/${this.options.roomId}/events/stream?after_sequence=${this.lastSequence}`;
  }

  async replay(): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/rooms/${this.options.roomId}/events?after_sequence=${this.lastSequence}`,
      { headers: { Authorization: `Bearer ${this.options.token}` }, cache: "no-store" }
    );
    if (!response.ok) {
      throw await parseApiError(response);
    }

    const body = (await response.json()) as { events: RoomEvent[]; latest_sequence: number };
    for (const event of body.events) {
      this.handleEvent(event);
    }
    if (body.latest_sequence > this.lastSequence) {
      this.lastSequence = body.latest_sequence;
      this.options.onSequence?.(this.lastSequence);
    }
  }

  handleEvent(event: Pick<RoomEvent, "sequence_no" | "event_type">): void {
    if (this.seen.has(event.sequence_no) || event.sequence_no <= this.lastSequence) {
      return;
    }

    this.seen.add(event.sequence_no);
    this.lastSequence = event.sequence_no;
    this.options.onSequence?.(event.sequence_no);
    void this.options.onRefetch();
  }

  start(): void {
    void this.connect();
    this.replayTimer = setInterval(() => void this.pollDurableEvents(), 3000);
  }

  stop(): void {
    this.controller?.abort();
    this.controller = null;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.replayTimer) {
      clearInterval(this.replayTimer);
      this.replayTimer = null;
    }
    this.options.onConnectionChange?.(false);
  }

  private async pollDurableEvents(): Promise<void> {
    if (this.replayInFlight) {
      return this.replayInFlight;
    }

    this.replayInFlight = this.replay()
      .catch(() => undefined)
      .finally(() => {
        this.replayInFlight = null;
      });
    return this.replayInFlight;
  }

  private async connect(): Promise<void> {
    this.controller = new AbortController();
    try {
      await this.replay();
      const response = await fetch(this.streamUrl(), {
        headers: { Authorization: `Bearer ${this.options.token}` },
        signal: this.controller.signal
      });
      if (!response.ok || !response.body) {
        throw response.ok ? new Error("Event stream unavailable") : await parseApiError(response);
      }
      this.options.onConnectionChange?.(true);
      await this.readSse(response.body);
    } catch {
      if (!this.controller?.signal.aborted) {
        this.options.onConnectionChange?.(false);
        this.reconnectTimer = setTimeout(() => void this.connect(), 1500);
      }
    }
  }

  private async readSse(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        return;
      }

      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split("\n\n");
      buffer = messages.pop() ?? "";
      for (const message of messages) {
        const dataLine = message
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (!dataLine) {
          continue;
        }
        this.handleEvent(JSON.parse(dataLine.slice(6)) as RoomEvent);
      }
    }
  }
}
