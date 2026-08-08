export type SplitMode = "equal" | "item_wise";
export type RoomStatus = "draft" | "active" | "settling" | "settled" | "archived" | "expired";
export type AdjustmentType =
  | "tax"
  | "service_charge"
  | "delivery_fee"
  | "packaging_fee"
  | "tip"
  | "discount"
  | "coupon"
  | "offer"
  | "adjustment"
  | "rounding";
export type AllocationMethod = "proportional" | "equal";
export type ItemAllocationMode = "individual" | "equal";

export type ApiErrorShape = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  detail?: string;
};

export type ApiError = Error & {
  status: number;
  code: string;
  details?: unknown;
};

export type Room = {
  id: string;
  status: RoomStatus;
  split_mode: SplitMode;
  payer_vpa: string | null;
  payer_name: string | null;
  title?: string | null;
  group_id?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
};

export type Participant = {
  id: string;
  room_id: string;
  user_id?: string | null;
  nickname: string;
  color: string;
  role: "creator" | "participant";
  joined_at: string;
};

export type Item = {
  id: string;
  receipt_id: string;
  name: string;
  quantity: number;
  total_paise: number;
  allocation_mode?: ItemAllocationMode;
  source: string;
  confidence: number;
  sort_order: number;
  version: number;
  created_at: string;
};

export type Assignment = {
  id: string;
  room_id: string;
  line_item_id: string;
  participant_id: string;
  claimed_qty: number;
  created_at: string;
};

export type Adjustment = {
  id: string;
  room_id: string;
  type: AdjustmentType;
  label: string;
  amount_paise: number;
  rate_basis_points: number | null;
  allocation_method: AllocationMethod;
  sort_order: number;
  version: number;
  created_at: string;
};

export type RoomCreateRequest = {
  split_mode: SplitMode;
  payer_name?: string;
  payer_vpa?: string;
  title?: string;
};

export type RoomCreateResponse = {
  room: Room;
  creator_token: string;
  invite_token: string;
};

export type RoomSummary = {
  room: Room;
  participants: Participant[];
  items: Item[];
  adjustments: Adjustment[];
  assignments: Assignment[];
};

export type JoinRoomResponse = {
  participant: Participant;
  participant_token: string;
};

export type ItemPayload = {
  name: string;
  quantity: number;
  total_paise: number;
  allocation_mode: ItemAllocationMode;
};

export type ClaimPayload = {
  item_version: number;
  claimed_qty: number;
};

export type AdjustmentPayload = {
  type: AdjustmentType;
  label: string;
  amount_paise: number;
  rate_basis_points?: number;
  allocation_method: AllocationMethod;
};

export type ParticipantTotal = {
  participant_id: string;
  items_paise: number;
  discount_paise: number;
  tax_paise: number;
  service_charge_paise: number;
  delivery_fee_paise: number;
  adjustment_paise: number;
  total_paise: number;
  is_payer: boolean;
};

export type SplitPreview = {
  grand_total_paise: number;
  participant_totals: ParticipantTotal[];
};

export type SettlementStatus =
  | "due"
  | "payment_opened"
  | "claimed_paid"
  | "payer_confirmed"
  | "disputed";

export type SettlementRequestSummary = {
  id: string;
  room_id: string;
  participant_id: string;
  amount_paise: number;
  amount_display: string;
  confirmed_amount_paise: number;
  pending_claim_amount_paise: number | null;
  remaining_amount_paise: number;
  remaining_amount_display: string;
  currency: "INR";
  payee_vpa: string;
  payee_name: string;
  payment_reference: string;
  status: SettlementStatus;
  created_at: string;
  updated_at: string;
  opened_at: string | null;
  claimed_paid_at: string | null;
  payer_confirmed_at: string | null;
  disputed_at: string | null;
};

export type SettlementAggregates = {
  due_count: number;
  payment_opened_count: number;
  claimed_paid_count: number;
  payer_confirmed_count: number;
  disputed_count: number;
  total_due_paise: number;
  total_confirmed_paise: number;
  total_original_paise: number;
};

export type SettlementSummary = {
  room_id: string;
  payer_details_configured: boolean;
  payee_vpa: string | null;
  payee_name: string | null;
  requests: SettlementRequestSummary[];
  aggregates: SettlementAggregates;
};

export type PayerDetailsInput = {
  payee_vpa: string;
  payee_name: string;
};

export type DisputeInput = {
  reason?: string | null;
};

export type AbuseReportReason =
  | "spam"
  | "fraud_suspected"
  | "wrong_payee"
  | "harassment"
  | "other";

export type AbuseReportInput = {
  reason: AbuseReportReason;
  message?: string | null;
};

export type AbuseReportResponse = {
  id: string;
  room_id: string;
  reason: AbuseReportReason;
  message: string | null;
  created_at: string;
};

export type OpenPaymentResponse = {
  settlement_request_id: string;
  status: SettlementStatus;
  amount_paise: number;
  amount_display: string;
  payee_vpa: string;
  payee_name: string;
  payment_reference: string;
  upi_uri: string;
  qr_payload: string;
  copy_vpa: string;
  disclaimer: string;
};

export type RoomEvent = {
  id?: string;
  room_id?: string;
  sequence_no: number;
  event_type: string;
  actor_id?: string | null;
  payload?: Record<string, unknown>;
  created_at?: string;
};

// --- OCR types ---

export type ParsedReceiptLine = {
  name: string;
  quantity: number;
  unit_price_paise: number | null;
  total_paise: number;
  confidence: number;
};

export type ParsedReceiptAdjustment = {
  type: string;
  label: string;
  amount_paise: number;
  allocation_method: string;
};

export type ReceiptUploadResponse = {
  receipt_id: string;
  image_id: string;
  job_id: string;
  status: string;
  parsed_receipt_id: string | null;
};

export type BrowserOcrCandidateLine = {
  text: string;
  poly: Array<{ x: number; y: number }>;
  score: number;
};

export type BrowserOcrCandidate = {
  provider: "paddleocr-js";
  model: string;
  language: string;
  raw_text: string;
  lines: BrowserOcrCandidateLine[];
};

export type OcrJobResponse = {
  id: string;
  room_id: string;
  receipt_id: string;
  image_id: string;
  provider: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  parsed_receipt_id: string | null;
};

export type ParsedReceiptDraftResponse = {
  id: string;
  room_id: string;
  receipt_id: string;
  ocr_job_id: string;
  merchant_name: string | null;
  subtotal_paise: number | null;
  tax_paise: number | null;
  discount_paise: number | null;
  total_paise: number | null;
  items: ParsedReceiptLine[];
  adjustments: ParsedReceiptAdjustment[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
  parser_version: string;
  status: string;
  redacted_raw_text: string | null;
};

export type ParsedReceiptUpdateRequest = {
  merchant_name?: string | null;
  subtotal_paise?: number | null;
  tax_paise?: number | null;
  discount_paise?: number | null;
  total_paise?: number | null;
  items?: ParsedReceiptLine[];
  adjustments?: ParsedReceiptAdjustment[];
  warnings?: string[];
  needs_review?: boolean;
};

export type ParsedReceiptConfirmResponse = {
  parsed_receipt_id: string;
  status: string;
  already_confirmed: boolean;
  created_item_ids: string[];
  created_adjustment_ids: string[];
  events: string[];
};

export type AuthUser = {
  id: string;
  provider: string;
  subject: string;
  email: string | null;
  username: string | null;
  display_name: string | null;
};

export type CommunityUser = Pick<AuthUser, "id" | "username" | "display_name">;

export type GroupMember = CommunityUser & { role: "owner" | "member" };

export type GroupBillSummary = {
  id: string;
  title: string;
  status: RoomStatus;
  created_at: string;
  grand_total_paise: number;
  pending_paise: number;
  cleared_paise: number;
  current_participant_id: string | null;
  is_creator: boolean;
};

export type Group = {
  id: string;
  name: string;
  role: "owner" | "member";
  members: GroupMember[];
  bills: GroupBillSummary[];
  total_paise: number;
  pending_paise: number;
  cleared_paise: number;
  created_at: string;
};
