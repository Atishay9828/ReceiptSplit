import type {
  Adjustment,
  AdjustmentPayload,
  ApiError,
  ApiErrorShape,
  Assignment,
  ClaimPayload,
  Item,
  ItemPayload,
  JoinRoomResponse,
  Room,
  RoomCreateRequest,
  RoomCreateResponse,
  RoomSummary,
  SplitPreview
} from "@/types/api";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorShape | null = null;
  try {
    body = (await response.json()) as ApiErrorShape;
  } catch {
    body = null;
  }

  const code = body?.error?.code ?? `HTTP_${response.status}`;
  const message =
    body?.error?.message ?? body?.detail ?? response.statusText ?? "Request failed";
  const error = new Error(message) as ApiError;
  error.status = response.status;
  error.code = code;
  error.details = body?.error?.details;
  return error;
}

type RequestOptions = {
  token?: string;
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number>;
};

export class ReceiptSplitApi {
  constructor(private readonly baseUrl = API_BASE_URL) {}

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    for (const [key, value] of Object.entries(options.query ?? {})) {
      url.searchParams.set(key, String(value));
    }

    const response = await fetch(url.toString(), {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {})
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store"
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  async createRoom(payload: RoomCreateRequest, token?: string): Promise<RoomCreateResponse> {
    const created = await this.request<RoomCreateResponse>("/api/rooms", {
      method: "POST",
      token,
      body: { split_mode: payload.split_mode }
    });

    const roomUpdates: Partial<Pick<Room, "payer_name" | "payer_vpa">> = {};
    if (payload.payer_name) {
      roomUpdates.payer_name = payload.payer_name;
    }
    if (payload.payer_vpa) {
      roomUpdates.payer_vpa = payload.payer_vpa;
    }

    if (Object.keys(roomUpdates).length > 0) {
      created.room = await this.updateRoom(created.room.id, created.creator_token, {
        version: created.room.version,
        ...roomUpdates
      });
    }

    return created;
  }

  updateRoom(roomId: string, token: string, body: Record<string, unknown>): Promise<Room> {
    return this.request<Room>(`/api/rooms/${roomId}`, { method: "PATCH", token, body });
  }

  getSummary(roomId: string, token: string): Promise<RoomSummary> {
    return this.request<RoomSummary>(`/api/rooms/${roomId}/summary`, { token });
  }

  joinRoom(roomId: string, inviteToken: string, nickname: string): Promise<JoinRoomResponse> {
    return this.request<JoinRoomResponse>(`/api/rooms/${roomId}/join`, {
      method: "POST",
      body: { invite_token: inviteToken, nickname }
    });
  }

  addItem(roomId: string, token: string, payload: ItemPayload): Promise<Item> {
    return this.request<Item>(`/api/rooms/${roomId}/items`, { method: "POST", token, body: payload });
  }

  updateItem(roomId: string, token: string, itemId: string, payload: ItemPayload & { version: number }) {
    return this.request<{ ok: true }>(`/api/rooms/${roomId}/items/${itemId}`, {
      method: "PATCH",
      token,
      body: payload
    });
  }

  deleteItem(roomId: string, token: string, itemId: string, version: number) {
    return this.request<{ ok: true }>(`/api/rooms/${roomId}/items/${itemId}`, {
      method: "DELETE",
      token,
      query: { version }
    });
  }

  addAdjustment(roomId: string, token: string, payload: AdjustmentPayload): Promise<Adjustment> {
    return this.request<Adjustment>(`/api/rooms/${roomId}/adjustments`, {
      method: "POST",
      token,
      body: payload
    });
  }

  claimItem(roomId: string, token: string, itemId: string, payload: ClaimPayload): Promise<Assignment> {
    return this.request<Assignment>(`/api/rooms/${roomId}/items/${itemId}/claim`, {
      method: "POST",
      token,
      body: payload
    });
  }

  unclaimItem(roomId: string, token: string, itemId: string) {
    return this.request<{ ok: true }>(`/api/rooms/${roomId}/items/${itemId}/claim`, {
      method: "DELETE",
      token
    });
  }

  previewSplit(roomId: string, token: string): Promise<SplitPreview> {
    return this.request<SplitPreview>(`/api/rooms/${roomId}/split/preview`, { token });
  }

  lockSplit(roomId: string, token: string, version: number) {
    return this.request(`/api/rooms/${roomId}/split/lock`, {
      method: "POST",
      token,
      body: { version }
    });
  }

  unlockSplit(roomId: string, token: string, version: number) {
    return this.request<{ ok: true }>(`/api/rooms/${roomId}/split/unlock`, {
      method: "POST",
      token,
      body: { version }
    });
  }
}

export const api = new ReceiptSplitApi();
