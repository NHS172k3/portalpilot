"use client";

import { useEffect, useState } from "react";

type HealthState =
  | { status: "loading"; label: "Checking" }
  | { status: "ok"; label: "API online" }
  | { status: "error"; label: "API unavailable" };

export function HealthPanel() {
  const [health, setHealth] = useState<HealthState>({
    status: "loading",
    label: "Checking",
  });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/health`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Health check failed: ${response.status}`);
        }
        const payload = (await response.json()) as { status?: string };
        setHealth(payload.status === "ok" ? { status: "ok", label: "API online" } : { status: "error", label: "API unavailable" });
      })
      .catch(() => {
        setHealth({ status: "error", label: "API unavailable" });
      });
  }, []);

  return (
    <section className="status-panel" aria-label="Backend health">
      <div className="status-row">
        <div>
          <div className="status-label">FastAPI health</div>
          <strong>{process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}</strong>
        </div>
        <span className={`status-value ${health.status === "error" ? "error" : ""}`}>
          {health.label}
        </span>
      </div>
    </section>
  );
}
