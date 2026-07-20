import type {
  Adjustment,
  AdjustmentPayload,
  AbuseReportInput,
  AbuseReportResponse,
  ApiError,
  ApiErrorShape,
  Assignment,
  AuthUser,
  ClaimPayload,
  CommunityUser,
  DisputeInput,
  Group,
  Item,
  ItemPayload,
  JoinRoomResponse,
  OcrJobResponse,
  OpenPaymentResponse,
  ParsedReceiptConfirmResponse,
  ParsedReceiptDraftResponse,
  ParsedReceiptUpdateRequest,
  PayerDetailsInput,
  ReceiptUploadResponse,
  Room,
  RoomCreateRequest,
  RoomCreateResponse,
  RoomSummary,
  SettlementRequestSummary,
  SettlementSummary,
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
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
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
      body: {
        split_mode: payload.split_mode,
        payer_name: payload.payer_name,
        payer_vpa: payload.payer_vpa,
        title: payload.title
      }
    });

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

  getSettlement(roomId: string, token: string): Promise<SettlementSummary> {
    return this.request<SettlementSummary>(`/api/rooms/${roomId}/settlement`, { token });
  }

  savePayerDetails(
    roomId: string,
    token: string,
    payload: PayerDetailsInput
  ): Promise<SettlementSummary> {
    return this.request<SettlementSummary>(`/api/rooms/${roomId}/settlement/payer`, {
      method: "PUT",
      token,
      body: payload
    });
  }

  prepareSettlement(roomId: string, token: string): Promise<SettlementSummary> {
    return this.request<SettlementSummary>(`/api/rooms/${roomId}/settlement/prepare`, {
      method: "POST",
      token
    });
  }

  openPayment(
    roomId: string,
    requestId: string,
    token: string
  ): Promise<OpenPaymentResponse> {
    return this.request<OpenPaymentResponse>(
      `/api/rooms/${roomId}/settlement/requests/${requestId}/open-payment`,
      { method: "POST", token }
    );
  }

  claimPaid(roomId: string, requestId: string, token: string): Promise<SettlementRequestSummary> {
    return this.request<SettlementRequestSummary>(
      `/api/rooms/${roomId}/settlement/requests/${requestId}/claim-paid`,
      { method: "POST", token }
    );
  }

  confirmSettlement(
    roomId: string,
    requestId: string,
    token: string
  ): Promise<SettlementRequestSummary> {
    return this.request<SettlementRequestSummary>(
      `/api/rooms/${roomId}/settlement/requests/${requestId}/confirm`,
      { method: "POST", token }
    );
  }

  disputeSettlement(
    roomId: string,
    requestId: string,
    token: string,
    payload: DisputeInput
  ): Promise<SettlementRequestSummary> {
    return this.request<SettlementRequestSummary>(
      `/api/rooms/${roomId}/settlement/requests/${requestId}/dispute`,
      { method: "POST", token, body: payload }
    );
  }

  reportAbuse(
    roomId: string,
    token: string,
    payload: AbuseReportInput
  ): Promise<AbuseReportResponse> {
    return this.request<AbuseReportResponse>(`/api/rooms/${roomId}/abuse-reports`, {
      method: "POST",
      token,
      body: payload
    });
  }

  removeParticipant(roomId: string, participantId: string, token: string): Promise<{ ok: true }> {
    return this.request<{ ok: true }>(`/api/rooms/${roomId}/participants/${participantId}`, {
      method: "DELETE",
      token
    });
  }

  getMe(token: string): Promise<AuthUser> {
    return this.request<AuthUser>("/api/auth/me", { token });
  }

  updateProfile(
    token: string,
    payload: { username: string; display_name: string }
  ): Promise<CommunityUser> {
    return this.request<CommunityUser>("/api/users/me/profile", {
      method: "PUT",
      token,
      body: payload
    });
  }

  listFriends(token: string): Promise<{ friends: CommunityUser[] }> {
    return this.request<{ friends: CommunityUser[] }>("/api/users/me/friends", { token });
  }

  addFriend(token: string, username: string): Promise<CommunityUser> {
    return this.request<CommunityUser>("/api/users/me/friends", {
      method: "POST",
      token,
      body: { username }
    });
  }

  listGroups(token: string): Promise<{ groups: Group[] }> {
    return this.request<{ groups: Group[] }>("/api/groups", { token });
  }

  createGroup(
    token: string,
    payload: { name: string; member_usernames: string[] }
  ): Promise<Group> {
    return this.request<Group>("/api/groups", { method: "POST", token, body: payload });
  }

  createGroupBill(
    token: string,
    groupId: string,
    payload: RoomCreateRequest & { title: string }
  ): Promise<{ bill: RoomCreateResponse }> {
    return this.request<{ bill: RoomCreateResponse }>(`/api/groups/${groupId}/bills`, {
      method: "POST",
      token,
      body: payload
    });
  }

  // --- OCR ---

  async uploadReceipt(roomId: string, token: string, file: File): Promise<ReceiptUploadResponse> {
    const form = new FormData();
    form.append("file", file);

    const response = await fetch(`${this.baseUrl}/api/rooms/${roomId}/receipts/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      cache: "no-store"
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }

    return (await response.json()) as ReceiptUploadResponse;
  }

  getOcrJob(roomId: string, token: string, jobId: string): Promise<OcrJobResponse> {
    return this.request<OcrJobResponse>(`/api/rooms/${roomId}/ocr-jobs/${jobId}`, { token });
  }

  getParsedReceipt(roomId: string, token: string, parsedReceiptId: string): Promise<ParsedReceiptDraftResponse> {
    return this.request<ParsedReceiptDraftResponse>(
      `/api/rooms/${roomId}/parsed-receipts/${parsedReceiptId}`,
      { token }
    );
  }

  getParsedReceiptDebug(roomId: string, token: string, parsedReceiptId: string): Promise<ParsedReceiptDraftResponse> {
    return this.request<ParsedReceiptDraftResponse>(
      `/api/rooms/${roomId}/parsed-receipts/${parsedReceiptId}`,
      { token, query: { include_raw_text: "true" } }
    );
  }

  updateParsedReceipt(
    roomId: string,
    token: string,
    parsedReceiptId: string,
    payload: ParsedReceiptUpdateRequest
  ): Promise<ParsedReceiptDraftResponse> {
    return this.request<ParsedReceiptDraftResponse>(
      `/api/rooms/${roomId}/parsed-receipts/${parsedReceiptId}`,
      { method: "PATCH", token, body: payload }
    );
  }

  confirmParsedReceipt(
    roomId: string,
    token: string,
    parsedReceiptId: string
  ): Promise<ParsedReceiptConfirmResponse> {
    return this.request<ParsedReceiptConfirmResponse>(
      `/api/rooms/${roomId}/parsed-receipts/${parsedReceiptId}/confirm`,
      { method: "POST", token }
    );
  }
}

export const api = new ReceiptSplitApi();
