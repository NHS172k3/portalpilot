"use client";

import { useEffect, useMemo, useState } from "react";
import type { ComponentType } from "react";
import { Activity, ArrowRight, Bot, CheckCircle2, Clock, FileText, ListChecks, PauseCircle, ShieldAlert } from "lucide-react";

import {
  AgentEvent,
  FieldRecord,
  TaskDetail,
  TaskStatus,
  TaskSummary,
  autoSuggestTasks,
  completeTaskReview,
  getTask,
  listTasks,
  manualAddTask,
  resumeAfterAuth,
  resolveTaskInfo,
  runLiveAgent,
  runWorkerTick,
} from "../api";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { TabsList, TabsTrigger } from "../../components/ui/tabs";
import { cn } from "../../lib/utils";

const tabs: { status: TaskStatus; label: string; icon: ComponentType<{ className?: string }> }[] = [
  { status: "not_started", label: "Not Started", icon: Clock },
  { status: "in_progress", label: "In Progress", icon: Activity },
  { status: "action_required", label: "Action Required", icon: PauseCircle },
  { status: "completed", label: "Completed", icon: CheckCircle2 },
];

export function QueueBoard() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [activeStatus, setActiveStatus] = useState<TaskStatus>("not_started");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [message, setMessage] = useState("");
  const [filingNeed, setFilingNeed] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh(nextSelectedId = selectedId) {
    const rows = await listTasks();
    setTasks(rows);
    const visible = rows.filter((task) => task.status === activeStatus);
    const nextId =
      nextSelectedId && visible.some((task) => task.id === nextSelectedId)
        ? nextSelectedId
        : visible[0]?.id ?? rows[0]?.id ?? null;
    setSelectedId(nextId);
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(error instanceof Error ? error.message : "Could not load queue"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeStatus]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    getTask(selectedId)
      .then(setDetail)
      .catch((error) => setMessage(error instanceof Error ? error.message : "Could not load task"));
  }, [selectedId]);

  async function handleTick() {
    setBusy(true);
    setMessage("");
    try {
      const result = await runWorkerTick();
      setMessage(result.picked ? `Worker picked ${result.task_id}` : result.reason ?? "No task picked");
      const rows = await listTasks();
      setTasks(rows);
      if (result.picked && result.task_id) {
        setActiveStatus("in_progress");
        setSelectedId(result.task_id);
        setDetail(await getTask(result.task_id));
      } else {
        await refresh(selectedId);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Worker failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleResolveInfo(fieldKey: string, value: string) {
    if (!detail) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await resolveTaskInfo(detail.id, fieldKey, value);
      setMessage(`Resolved field and resumed task: ${result.status.replace("_", " ")}`);
      await refresh(detail.id);
      setDetail(await getTask(detail.id));
      setActiveStatus(result.status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not resolve blocker");
    } finally {
      setBusy(false);
    }
  }

  async function handleCompleteReview() {
    if (!detail) return;
    setBusy(true);
    setMessage("");
    try {
      const completed = await completeTaskReview(detail.id);
      setMessage("Review completed");
      await refresh(completed.id);
      setDetail(completed);
      setActiveStatus("completed");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not complete review");
    } finally {
      setBusy(false);
    }
  }

  async function handleAutoSuggest() {
    const profileId = detail?.business_profile_id ?? tasks[0]?.business_profile_id;
    if (!profileId) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await autoSuggestTasks(profileId);
      setMessage(`Added ${result.count} researched filing${result.count === 1 ? "" : "s"}`);
      await refresh(selectedId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not research suggestions");
    } finally {
      setBusy(false);
    }
  }

  async function handleManualAdd() {
    const profileId = detail?.business_profile_id ?? tasks[0]?.business_profile_id;
    const need = filingNeed.trim();
    if (!profileId || !need) return;
    setBusy(true);
    setMessage("");
    try {
      const created = await manualAddTask(profileId, need);
      setFilingNeed("");
      setMessage("Added researched filing");
      setActiveStatus("not_started");
      await refresh(created.id);
      setSelectedId(created.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not add filing");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunLive() {
    if (!detail?.form_definition_id) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await runLiveAgent(detail.id);
      setMessage(`Live portal handoff: ${result.status.replace("_", " ")}`);
      await refresh(detail.id);
      setDetail(await getTask(detail.id));
      setActiveStatus("action_required");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not reach live portal");
    } finally {
      setBusy(false);
    }
  }

  async function handleResumeAfterAuth() {
    if (!detail) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await resumeAfterAuth(detail.id);
      setMessage(`Agent resumed: ${result.status.replace("_", " ")}`);
      await refresh(detail.id);
      setDetail(await getTask(detail.id));
      setActiveStatus(result.status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not resume after access handoff");
    } finally {
      setBusy(false);
    }
  }

  const counts = useMemo(() => {
    return tabs.reduce<Record<TaskStatus, number>>(
      (memo, tab) => ({ ...memo, [tab.status]: tasks.filter((task) => task.status === tab.status).length }),
      { not_started: 0, in_progress: 0, action_required: 0, completed: 0 },
    );
  }, [tasks]);

  const visibleTasks = tasks.filter((task) => task.status === activeStatus);

  return (
    <main className="min-h-screen bg-[#F7F7F5] px-8 py-6 text-[#0D0D0D]">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex gap-4 border-b border-[#D9D9D2] pb-5 items-end justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-normal text-[#10A37F]">PortalPilot</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-[#0D0D0D]">Filing queue</h1>
            <p className="mt-2 text-sm text-[#6B6B66]">{tasks.length} queued filings across the workspace</p>
          </div>
          <div className="grid w-[620px] gap-2">
            <div className="flex justify-end gap-2">
              <Button disabled={busy} onClick={handleAutoSuggest} type="button" variant="secondary">
                Auto-suggest
              </Button>
              <Button disabled={busy} onClick={handleTick} type="button">
                <Bot className="h-4 w-4" />
                Run worker
              </Button>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
              <input
                className="min-h-10 rounded-md border border-[#D9D9D2] bg-white px-3 text-sm text-[#0D0D0D] outline-none focus:border-[#10A37F]"
                onChange={(event) => setFilingNeed(event.target.value)}
                placeholder="Manual add: describe a filing need"
                value={filingNeed}
              />
              <Button disabled={busy || !filingNeed.trim()} onClick={handleManualAdd} type="button" variant="outline">
                Research add
              </Button>
            </div>
          </div>
        </header>

        {message ? (
          <div className="rounded-lg border border-[#B7E4D5] bg-[#E7F4EF] px-4 py-3 text-sm font-medium text-[#0E7A5F]">
            {message}
          </div>
        ) : null}

        <TabsList className="grid-cols-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <TabsTrigger
                active={activeStatus === tab.status}
                key={tab.status}
                onClick={() => setActiveStatus(tab.status)}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{tab.label}</span>
                </span>
                <Badge variant={activeStatus === tab.status ? "success" : "secondary"}>{counts[tab.status]}</Badge>
              </TabsTrigger>
            );
          })}
        </TabsList>

        <div className="grid gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
          <Card className="overflow-hidden">
            <CardHeader className="border-b border-[#ECECE7]">
              <CardTitle className="flex items-center gap-2">
                <ListChecks className="h-4 w-4 text-[#10A37F]" />
                Tasks
              </CardTitle>
              <CardDescription>{tabs.find((tab) => tab.status === activeStatus)?.label}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 p-3">
              {visibleTasks.length ? (
                visibleTasks.map((task) => (
                  <TaskCard
                    active={task.id === selectedId}
                    key={task.id}
                    onClick={() => setSelectedId(task.id)}
                    task={task}
                  />
                ))
              ) : (
                <EmptyState label="No tasks in this tab" />
              )}
            </CardContent>
          </Card>

          <Card className="min-w-0 overflow-hidden">
            {detail ? (
              <TaskDetailView
                busy={busy}
                detail={detail}
                onCompleteReview={handleCompleteReview}
                onResumeAfterAuth={handleResumeAfterAuth}
                onRunLive={handleRunLive}
                onResolveInfo={handleResolveInfo}
              />
            ) : (
              <EmptyState label="Select a task" />
            )}
          </Card>
        </div>
      </div>
    </main>
  );
}

function TaskCard({ active, onClick, task }: { active: boolean; onClick: () => void; task: TaskSummary }) {
  return (
    <button
      className={cn(
        "group grid w-full gap-2 rounded-lg border p-3 text-left transition-colors",
        active ? "border-[#10A37F] bg-[#E7F4EF]" : "border-[#D9D9D2] bg-white hover:border-[#BEBEB7] hover:bg-[#F7F7F5]",
      )}
      onClick={onClick}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <strong className="min-w-0 text-sm font-semibold leading-5 text-[#0D0D0D]">{task.form_name ?? task.notes ?? task.id}</strong>
        <ArrowRight className={cn("mt-0.5 h-4 w-4 shrink-0 text-[#C9C9C2]", active && "text-[#10A37F]")} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge variant={statusVariant(task.status)}>{task.status.replace("_", " ")}</Badge>
        {task.jurisdiction || task.agency ? <Badge variant="outline">{[task.jurisdiction, task.agency].filter(Boolean).join(" · ")}</Badge> : null}
      </div>
      {task.blocker?.message ? <p className="text-xs leading-5 text-amber-700">{task.blocker.message}</p> : null}
    </button>
  );
}

function TaskDetailView({
  busy,
  detail,
  onCompleteReview,
  onResumeAfterAuth,
  onRunLive,
  onResolveInfo,
}: {
  busy: boolean;
  detail: TaskDetail;
  onCompleteReview: () => Promise<void>;
  onResumeAfterAuth: () => Promise<void>;
  onRunLive: () => Promise<void>;
  onResolveInfo: (fieldKey: string, value: string) => Promise<void>;
}) {
  return (
    <>
      <CardHeader className="border-b border-[#ECECE7]">
        <div className="flex gap-3 items-start justify-between">
          <div className="min-w-0">
            <CardDescription>Task detail</CardDescription>
            <CardTitle className="mt-1 leading-6">{detail.form_name ?? detail.notes ?? detail.id}</CardTitle>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {detail.form_definition_id ? (
              <>
                <a
                  className="inline-flex h-9 items-center justify-center rounded-md border border-[#C9C9C2] bg-white px-3 text-sm font-semibold text-[#0D0D0D] hover:bg-[#F7F7F5]"
                  href={`/mirror/${detail.form_definition_id}?taskId=${detail.id}`}
                  target="_blank"
                >
                  Open mirror draft
                </a>
                <a
                  className="inline-flex h-9 items-center justify-center rounded-md bg-[#10A37F] px-3 text-sm font-semibold text-white hover:bg-[#0E8F70]"
                  href={`/mirror/${detail.form_definition_id}?taskId=${detail.id}&replay=1`}
                  target="_blank"
                >
                  Replay fill
                </a>
              </>
            ) : null}
            <Badge variant={statusVariant(detail.status)}>{detail.status.replace("_", " ")}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 p-4">
        <ActionPanel
          busy={busy}
          detail={detail}
          onCompleteReview={onCompleteReview}
          onResumeAfterAuth={onResumeAfterAuth}
          onRunLive={onRunLive}
          onResolveInfo={onResolveInfo}
        />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)]">
          <div className="grid gap-4">
            <RecommendationPanel detail={detail} />
            <RecordList records={detail.field_records} />
          </div>
          <EventList events={detail.agent_events} />
        </div>
      </CardContent>
    </>
  );
}

function ActionPanel({
  busy,
  detail,
  onCompleteReview,
  onResumeAfterAuth,
  onRunLive,
  onResolveInfo,
}: {
  busy: boolean;
  detail: TaskDetail;
  onCompleteReview: () => Promise<void>;
  onResumeAfterAuth: () => Promise<void>;
  onRunLive: () => Promise<void>;
  onResolveInfo: (fieldKey: string, value: string) => Promise<void>;
}) {
  const neededField = detail.blocker?.needed_fields?.[0];
  const [value, setValue] = useState("");

  useEffect(() => {
    setValue("");
  }, [detail.id, neededField?.key]);

  if (detail.status === "action_required" && detail.blocker?.type === "info_required" && neededField) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="mb-3 flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <div>
            <h2 className="text-sm font-semibold text-amber-950">{detail.blocker.message}</h2>
            <p className="mt-1 text-sm text-amber-800">{neededField.section} · {neededField.reason}</p>
          </div>
        </div>
        <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
          <input
            className="min-h-10 rounded-md border border-amber-200 bg-white px-3 text-sm text-[#0D0D0D] outline-none focus:border-[#10A37F]"
            onChange={(event) => setValue(event.target.value)}
            placeholder={neededField.label}
            value={value}
          />
          <Button disabled={busy || !value.trim()} onClick={() => onResolveInfo(neededField.key, value)} type="button">
            Supply info
          </Button>
        </div>
      </section>
    );
  }

  if (detail.status === "action_required" && detail.blocker?.type === "auth_required") {
    return (
      <section className="flex items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <div>
            <h2 className="text-sm font-semibold text-amber-950">{detail.blocker.message}</h2>
            <p className="mt-1 text-sm text-amber-800">Complete the human-only step, then hand control back to the agent.</p>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          {detail.blocker.portal_url ? (
            <a
              className="inline-flex h-10 items-center justify-center rounded-md border border-[#C9C9C2] bg-white px-4 text-sm font-semibold text-[#0D0D0D] hover:bg-[#F7F7F5]"
              href={detail.blocker.portal_url}
              rel="noreferrer"
              target="_blank"
            >
              Open portal
            </a>
          ) : null}
          <Button disabled={busy} onClick={onResumeAfterAuth} type="button">
            I authenticated
          </Button>
        </div>
      </section>
    );
  }

  if (detail.form_definition_id && detail.status !== "completed") {
    return (
      <section className="flex items-center justify-between gap-4 rounded-lg border border-[#D9D9D2] bg-white p-4">
        <div>
          <h2 className="text-sm font-semibold text-[#0D0D0D]">Live portal handoff</h2>
          <p className="mt-1 text-sm text-[#6B6B66]">Reach the real portal and stop at login, CAPTCHA, or another human-only wall.</p>
        </div>
        <Button disabled={busy} onClick={onRunLive} type="button" variant="outline">
          Try live portal
        </Button>
      </section>
    );
  }

  if (detail.status === "in_progress" && detail.field_records.length > 0) {
    return (
      <section className="flex items-center justify-between gap-4 rounded-lg border border-[#B7E4D5] bg-[#E7F4EF] p-4">
        <div>
          <h2 className="text-sm font-semibold text-[#0E7A5F]">Ready for review</h2>
          <p className="mt-1 text-sm text-[#0E7A5F]">The agent filled available fields and stopped before human-only actions.</p>
        </div>
        <Button disabled={busy} onClick={onCompleteReview} type="button">
          Mark reviewed
        </Button>
      </section>
    );
  }

  return null;
}

function RecommendationPanel({ detail }: { detail: TaskDetail }) {
  const recommendation = detail.recommendation;
  if (!recommendation) {
    return (
      <section className="rounded-lg border border-dashed border-[#C9C9C2] bg-[#F7F7F5] p-4 text-sm text-[#6B6B66]">
        No research recommendation attached yet
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-[#D9D9D2] bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[#0D0D0D]">Research evidence</h2>
          <p className="mt-1 text-sm leading-5 text-[#4A4A46]">{recommendation.reason}</p>
        </div>
        <Badge variant="outline">{Math.round(recommendation.confidence * 100)}%</Badge>
      </div>
      <div className="grid gap-3 text-sm text-[#4A4A46]">
        {recommendation.fee || recommendation.timeline ? (
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md bg-[#F7F7F5] p-3">
              <strong className="block text-[#0D0D0D]">Fee</strong>
              {recommendation.fee ?? "Not found"}
            </div>
            <div className="rounded-md bg-[#F7F7F5] p-3">
              <strong className="block text-[#0D0D0D]">Timeline</strong>
              {recommendation.timeline ?? "Not found"}
            </div>
          </div>
        ) : null}
        {recommendation.source_links.length ? (
          <div className="flex flex-wrap gap-2">
            {recommendation.source_links.map((source) => (
              <a
                className="rounded-full border border-[#D9D9D2] bg-[#F7F7F5] px-3 py-1 text-xs font-semibold text-[#0E7A5F]"
                href={source.url}
                key={source.url}
                rel="noreferrer"
                target="_blank"
              >
                {source.title}
              </a>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function RecordList({ records }: { records: FieldRecord[] }) {
  return (
    <section className="rounded-lg border border-[#D9D9D2] bg-[#F7F7F5]/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-[#0D0D0D]">Fill map</h2>
        <Badge variant="outline">{records.length}</Badge>
      </div>
      {records.length ? (
        <div className="grid max-h-[680px] gap-2 overflow-auto pr-1">
          {records.slice(0, 90).map((record) => (
            <div className="rounded-md border border-[#D9D9D2] bg-white p-3" key={record.field_key}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <strong className="block text-sm font-semibold leading-5 text-[#0D0D0D]">{record.label}</strong>
                  <span className="text-xs text-[#6B6B66]">{record.section}</span>
                </div>
                <Badge variant={recordVariant(record.status)}>{record.status.replace("_", " ")}</Badge>
              </div>
              <p className="mt-2 text-sm leading-5 text-[#4A4A46] [overflow-wrap:anywhere]">{record.proposed_value ?? record.reason}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState label="No field records yet" />
      )}
    </section>
  );
}

function EventList({ events }: { events: AgentEvent[] }) {
  return (
    <section className="rounded-lg border border-[#D9D9D2] bg-[#F7F7F5]/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-[#0D0D0D]">Event log</h2>
        <Badge variant="outline">{events.length}</Badge>
      </div>
      {events.length ? (
        <div className="grid max-h-[680px] gap-2 overflow-auto pr-1">
          {events.map((event, index) => (
            <div className="flex items-start gap-3 rounded-md border border-[#D9D9D2] bg-white p-3" key={`${event.timestamp}-${index}`}>
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#9B9B94]" />
              <div className="min-w-0">
                <strong className="block text-sm font-semibold text-[#0D0D0D]">{event.type}</strong>
                <span className="text-xs text-[#6B6B66]">{new Date(event.timestamp).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState label="No events yet" />
      )}
    </section>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex min-h-28 items-center justify-center rounded-lg border border-dashed border-[#C9C9C2] bg-[#F7F7F5] p-6 text-center text-sm text-[#6B6B66]">
      {label}
    </div>
  );
}

function statusVariant(status: TaskStatus) {
  if (status === "in_progress") return "success";
  if (status === "action_required") return "warning";
  if (status === "completed") return "default";
  return "secondary";
}

function recordVariant(status: string) {
  if (status === "filled") return "success";
  if (status === "needs_review" || status === "user_required") return "warning";
  if (status === "blocked") return "destructive";
  return "secondary";
}
