import type { CompanyProfile, ComputerUseAccessSessionResponse, ComputerUseRunResponse, Dashboard, DocumentExtractResponse, FilingDetail } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiUrl() {
  return API_URL;
}

export function isLocalApiUrl() {
  try {
    const host = new URL(API_URL).hostname;
    return host === "localhost" || host === "127.0.0.1" || host === "::1";
  } catch {
    return false;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new Error(`Could not reach PortalPilot API at ${API_URL}. Check NEXT_PUBLIC_API_URL and the FastAPI server.`);
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getDashboard() {
  return request<Dashboard>("/dashboard");
}

export function createFiling(description: string, companyContext?: string) {
  return request<FilingDetail>("/filings/describe", {
    method: "POST",
    body: JSON.stringify({ description, company_context: companyContext || null }),
  });
}

export function getFiling(id: string) {
  return request<FilingDetail>(`/filings/${id}`);
}

export function answerRequest(id: string, answer: string) {
  return request(`/agent-requests/${id}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer, save_to_profile: true }),
  });
}

export function getProfile() {
  return request<CompanyProfile>("/profile");
}

export function updateProfile(profile: CompanyProfile) {
  return request<CompanyProfile>("/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export function extractDocument(fileName: string, content: string) {
  return request<DocumentExtractResponse>("/documents/extract", {
    method: "POST",
    body: JSON.stringify({ file_name: fileName, content }),
  });
}

export function runComputerUse(filingId: string, targetUrl: string) {
  return request<ComputerUseRunResponse>(`/filings/${filingId}/computer-use`, {
    method: "POST",
    body: JSON.stringify({ target_url: targetUrl, max_steps: 3, allow_user_handoff: true, handoff_timeout_seconds: 180 }),
  });
}

export function startComputerUseAccessSession(filingId: string, targetUrl: string) {
  return request<ComputerUseAccessSessionResponse>(`/filings/${filingId}/computer-use/access-session`, {
    method: "POST",
    body: JSON.stringify({ target_url: targetUrl, max_steps: 3, allow_user_handoff: true, handoff_timeout_seconds: 300 }),
  });
}

export function resumeComputerUseAccessSession(filingId: string, sessionId: string, targetUrl: string) {
  return request<ComputerUseRunResponse>(`/filings/${filingId}/computer-use/access-session/${sessionId}/resume`, {
    method: "POST",
    body: JSON.stringify({ target_url: targetUrl, max_steps: 3, allow_user_handoff: true, handoff_timeout_seconds: 300 }),
  });
}

export function closeComputerUseAccessSession(filingId: string, sessionId: string) {
  return request<{ closed: boolean }>(`/filings/${filingId}/computer-use/access-session/${sessionId}`, {
    method: "DELETE",
  });
}
