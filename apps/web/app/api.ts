export type Attribute = {
  id: number;
  key: string;
  label: string;
  value: string;
  sensitivity: string;
  notes: string | null;
};

export type Profile = {
  id: string;
  name: string;
  attribute_count?: number;
  attributes?: Attribute[];
};

export type Fact = {
  id: string;
  key: string;
  value: string;
  evidence_note: string | null;
  confidence: number;
  sensitivity: string;
};

export type DocumentRecord = {
  id: string;
  filename: string;
  mime: string;
  created_at: string;
  facts: Fact[];
};

export type FormField = {
  id: number;
  key: string;
  label: string;
  section: string;
  type: string;
  options: string[] | null;
  sensitivity: string;
  required: boolean;
  human_only: boolean;
  provenance: string;
  conditional_on: string | null;
  notes: string | null;
};

export type FormDefinition = {
  id: string;
  jurisdiction: string;
  agency: string;
  name: string;
  portal_url: string | null;
  notes: string | null;
  fields: FormField[];
};

export type TaskStatus = "not_started" | "in_progress" | "action_required" | "completed";

export type TaskBlocker = {
  type?: "auth_required" | "info_required";
  message?: string;
  needed_action?: "open_portal" | "provide_info";
  portal_url?: string;
  needed_fields?: { key: string; label: string; section: string; reason: string }[];
};

export type TaskSummary = {
  id: string;
  business_profile_id: string;
  status: TaskStatus;
  origin: string;
  blocker: TaskBlocker | null;
  notes: string | null;
  profile_name: string;
  form_name: string | null;
  agency: string | null;
  jurisdiction: string | null;
  form_definition_id: string | null;
};

export type FieldRecord = {
  field_key: string;
  label: string;
  section: string;
  proposed_value: string | null;
  confidence: number;
  sensitivity: string;
  status: string;
  reason: string;
};

export type AgentEvent = {
  type: string;
  payload: unknown;
  timestamp: string;
};

export type Recommendation = {
  reason: string;
  prerequisites: string[];
  fee: string | null;
  timeline: string | null;
  warnings: string[];
  source_links: { title: string; url: string }[];
  confidence: number;
};

export type TaskDetail = TaskSummary & {
  field_records: FieldRecord[];
  agent_events: AgentEvent[];
  recommendation: Recommendation | null;
};

export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function listProfiles() {
  return request<Profile[]>("/profiles");
}

export function getProfile(profileId: string) {
  return request<Profile>(`/profiles/${profileId}`);
}

export function createProfile(name: string) {
  return request<Profile>("/profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function upsertAttribute(profileId: string, payload: Omit<Attribute, "id">) {
  return request<Attribute>(`/profiles/${profileId}/attributes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listDocuments(profileId: string) {
  return request<DocumentRecord[]>(`/profiles/${profileId}/documents`);
}

export function uploadDocument(profileId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentRecord>(`/profiles/${profileId}/documents`, {
    method: "POST",
    body: formData,
  });
}

export function getForm(formId: string) {
  return request<FormDefinition>(`/forms/${formId}`);
}

export function listTasks() {
  return request<TaskSummary[]>("/tasks");
}

export function getTask(taskId: string) {
  return request<TaskDetail>(`/tasks/${taskId}`);
}

export function runWorkerTick() {
  return request<{ picked: boolean; task_id?: string; result?: unknown; reason?: string }>("/worker/tick", {
    method: "POST",
  });
}

export function runLiveAgent(taskId: string) {
  return request<{ task_id: string; status: TaskStatus; blocker?: TaskBlocker }>(`/tasks/${taskId}/run-live-agent`, {
    method: "POST",
  });
}

export function resumeAfterAuth(taskId: string) {
  return request<{ task_id: string; status: TaskStatus }>(`/tasks/${taskId}/resume-after-auth`, {
    method: "POST",
  });
}

export function resolveTaskInfo(taskId: string, fieldKey: string, value: string) {
  return request<{ task_id: string; status: TaskStatus }>(`/tasks/${taskId}/resolve-info`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ field_key: fieldKey, value }),
  });
}

export function completeTaskReview(taskId: string) {
  return request<TaskDetail>(`/tasks/${taskId}/complete-review`, {
    method: "POST",
  });
}

export function autoSuggestTasks(profileId: string) {
  return request<{ count: number; created: TaskSummary[] }>("/research/auto-suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId }),
  });
}

export function manualAddTask(profileId: string, filingNeed: string) {
  return request<TaskSummary>("/research/manual-add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId, filing_need: filingNeed }),
  });
}
