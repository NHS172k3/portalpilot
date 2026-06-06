export type FilingStatus =
  | "not_started"
  | "in_progress"
  | "needs_you"
  | "ready_for_review"
  | "completed"
  | "blocked"
  | "archived";

export type RequestType = "data_request" | "human_wall_handoff" | "confirmation" | "warning";

export type FilingCard = {
  id: string;
  name: string;
  jurisdiction: string;
  agency: string;
  status: FilingStatus;
  progress: number;
  last_agent_action: string;
  updated_at: string;
  open_requests: number;
  deadline?: string | null;
};

export type ActionRequest = {
  id: string;
  filing_id: string;
  filing_name: string;
  request_type: RequestType;
  title: string;
  prompt: string;
  why_needed: string;
  field_key?: string | null;
  proposed_answer?: string | null;
  confidence?: number | null;
  source_type?: string | null;
  portal_url?: string | null;
  status: string;
  created_at: string;
};

export type ActivityEvent = {
  event_type: string;
  summary: string;
  detail?: string | null;
};

export type Recommendation = {
  filing_name: string;
  jurisdiction: string;
  agency: string;
  reason: string;
  prerequisites: string[];
  fee_expectation?: string | null;
  deadline?: string | null;
  warnings: string[];
  confidence: number;
  sources: { title: string; url: string; summary: string }[];
};

export type ChecklistItem = { label: string; status: string; reason: string };

export type FieldConfidence = {
  field_key?: string | null;
  selector?: string | null;
  input_kind?: string | null;
  portal_section: string;
  field_label: string;
  proposed_value?: string | null;
  source_type: string;
  confidence: number;
  sensitivity: string;
  status: string;
  reason: string;
};

export type Dashboard = {
  needs_you_count: number;
  in_progress_count: number;
  upcoming_deadlines: number;
  board: Record<FilingStatus, FilingCard[]>;
  requests: ActionRequest[];
  recent_activity: ActivityEvent[];
};

export type FilingDetail = {
  card: FilingCard;
  recommendation: Recommendation;
  checklist: ChecklistItem[];
  fields: FieldConfidence[];
  requests: ActionRequest[];
  activity: ActivityEvent[];
};

export type CompanyProfile = {
  legal_name?: string | null;
  trading_name?: string | null;
  registration_id?: string | null;
  address?: string | null;
  industry_summary?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  filing_notes?: string | null;
};

export type DocumentExtractResponse = {
  document_id: string;
  file_name: string;
  status: string;
  facts: {
    label: string;
    value?: string | null;
    source_type: string;
    confidence: number;
    sensitivity: string;
    evidence_note?: string | null;
  }[];
  activity: ActivityEvent;
};

export type ComputerUseStep = {
  step: number;
  action_type: string;
  status: string;
  summary: string;
  blocked_reason?: string | null;
  current_url?: string | null;
};

export type ComputerUseRunResponse = {
  status: string;
  mode: string;
  target_url: string;
  current_url?: string | null;
  recommendation?: Recommendation | null;
  checklist: ChecklistItem[];
  fields: FieldConfidence[];
  user_handoff_used: boolean;
  user_handoff_timed_out: boolean;
  steps: ComputerUseStep[];
  requests: {
    request_type: RequestType;
    title: string;
    prompt: string;
    why_needed: string;
    field_key?: string | null;
    proposed_answer?: string | null;
    confidence?: number | null;
    source_type?: string | null;
    portal_url?: string | null;
  }[];
  activity: ActivityEvent[];
  blocked_reason?: string | null;
  agents: string[];
};

export type ComputerUseAccessSessionResponse = {
  session_id: string;
  status: string;
  target_url: string;
  current_url?: string | null;
  handoff_reason?: string | null;
  prompt: string;
};
