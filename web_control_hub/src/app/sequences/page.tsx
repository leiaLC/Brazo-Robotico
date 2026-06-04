"use client";

import { Pause, Play, Square, Wifi, WifiOff } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Card, IndustrialButton, PageTitle, ProgressBar, StatusPill } from "@/components/ui";
import { sequences } from "@/lib/mock-data";

type RequestState = "idle" | "running" | "ok" | "error";
type ConnectionState = "connecting" | "connected" | "disconnected" | "error";
type TaskStatus = {
  mode: string;
  current_task: string;
  message: string;
  progress: number;
  error_code: string;
  estop_active?: boolean;
};

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function getBackendWebSocketUrl(backendUrl: string): string | null {
  try {
    const url = new URL(backendUrl);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/task-status";
    url.search = "";
    return url.toString();
  } catch {
    return null;
  }
}

function clampProgress(value: number) {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function sequenceIdFromTask(task: string) {
  const match = task.match(/^sequence\s+(.+)$/i);
  return match?.[1] ?? null;
}

export default function SequencesPage() {
  // SSR-stable initial value: no llamamos a window aqui para que el primer
  // render del servidor y del cliente coincidan (evita el hydration mismatch).
  // El valor basado en window.location se aplica tras montar, en un useEffect.
  const [backendUrl, setBackendUrl] = useState(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? "",
  );
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [activeSequenceId, setActiveSequenceId] = useState<string | null>(null);
  const [message, setMessage] = useState("Ready");
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [sequenceProgress, setSequenceProgress] = useState(0);
  const activeSequenceRef = useRef<string | null>(null);
  const active = useMemo(
    () => sequences.find((sequence) => sequence.id === activeSequenceId),
    [activeSequenceId],
  );
  const ActiveIcon = active?.icon;
  const connected = connectionState === "connected" && requestState !== "error";
  const estopActive = useMemo(
    () => Boolean(taskStatus?.estop_active) || taskStatus?.mode === "ESTOP",
    [taskStatus],
  );
  const isPaused = useMemo(() => {
    if (estopActive) {
      return false;
    }
    const msg = taskStatus?.message?.toLowerCase() ?? "";
    return msg.startsWith("paused") || msg.startsWith("resuming");
  }, [taskStatus, estopActive]);

  useEffect(() => {
    activeSequenceRef.current = activeSequenceId;
  }, [activeSequenceId]);

  // Tras montar en el cliente, si no hay URL fijada por env, derivarla de
  // window.location. Esto ocurre despues de la hidratacion, por lo que no
  // provoca mismatch entre servidor y cliente.
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_BACKEND_URL) {
      setBackendUrl((current) => current || getDefaultBackendUrl());
    }
  }, []);

  useEffect(() => {
    const wsUrl = backendUrl ? getBackendWebSocketUrl(backendUrl) : null;
    if (!wsUrl) {
      return;
    }

    const socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => setConnectionState("connected"));
    socket.addEventListener("error", () => setConnectionState("error"));
    socket.addEventListener("close", () => setConnectionState("disconnected"));
    socket.addEventListener("message", (event) => {
      const nextStatus = JSON.parse(event.data) as TaskStatus;
      setTaskStatus(nextStatus);

      const statusSequenceId = sequenceIdFromTask(nextStatus.current_task);
      if (statusSequenceId) {
        activeSequenceRef.current = statusSequenceId;
        setActiveSequenceId(statusSequenceId);
      }

      if (nextStatus.mode === "WEB_SEQUENCE" || statusSequenceId) {
        setSequenceProgress(clampProgress(nextStatus.progress * 100));
        setMessage(nextStatus.message || "Sequence running");
        return;
      }

      if (activeSequenceRef.current && nextStatus.progress >= 1.0) {
        setSequenceProgress(100);
        setMessage(nextStatus.message || "Sequence complete");
      }
    });

    return () => {
      socket.close();
    };
  }, [backendUrl]);

  function updateBackendUrl(value: string) {
    setBackendUrl(value);
    setRequestState("idle");
    setActiveSequenceId(null);
    setSequenceProgress(0);
    setMessage("Ready");
  }

  async function runSequence(sequenceId: string) {
    setRequestState("running");
    activeSequenceRef.current = sequenceId;
    setActiveSequenceId(sequenceId);
    setSequenceProgress(0);
    setMessage(`Sending ${sequenceId}`);

    const response = await fetch(`${backendUrl}/sequence/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sequence_id: sequenceId }),
    });

    if (!response.ok) {
      const detail = await response.text();
      setRequestState("error");
      setMessage(detail || "Sequence request failed");
      return;
    }

    setRequestState("ok");
    setMessage(`Running ${sequenceId}`);
  }

  async function cancelTask() {
    setRequestState("running");
    const response = await fetch(`${backendUrl}/task/cancel`, { method: "POST" });
    activeSequenceRef.current = null;
    setActiveSequenceId(null);
    setSequenceProgress(0);
    setRequestState(response.ok ? "ok" : "error");
    setMessage(response.ok ? "Cancel sent" : "Cancel failed");
  }

  async function pauseTask() {
    setRequestState("running");
    try {
      const response = await fetch(`${backendUrl}/task/pause`, { method: "POST" });
      setRequestState(response.ok ? "ok" : "error");
      setMessage(response.ok ? "Pause sent" : "Pause failed");
    } catch (error) {
      setRequestState("error");
      setMessage("Pause request failed");
    }
  }

  async function resumeTask() {
    setRequestState("running");
    try {
      const response = await fetch(`${backendUrl}/task/resume`, { method: "POST" });
      setRequestState(response.ok ? "ok" : "error");
      setMessage(response.ok ? "Resume sent" : "Resume failed");
    } catch (error) {
      setRequestState("error");
      setMessage("Resume request failed");
    }
  }

  return (
    <div className="pb-28">
      <div className="mx-auto mb-16 max-w-6xl">
        <PageTitle
          action={
            <StatusPill icon={connected ? Wifi : WifiOff} tone={connected ? "green" : "red"}>
              {message}
            </StatusPill>
          }
          centered
          subtitle="Select a sequence to initiate automated operations."
          title="Sequences"
        />
        <label className="mx-auto mt-6 grid max-w-xl gap-2">
          <span className="text-xs font-black uppercase tracking-[0.12em] text-[#29303A]">
            Backend gateway URL
          </span>
          <input
            className="min-h-12 rounded border border-[#BFC7D2] bg-white px-4 font-mono text-sm outline-none focus:border-[#003C69] focus:ring-2 focus:ring-[#CFE1F6]"
            onChange={(event) => updateBackendUrl(event.target.value)}
            value={backendUrl}
          />
        </label>
      </div>

      <section className="mx-auto grid max-w-[1360px] gap-6 lg:grid-cols-2">
        {sequences.map((sequence) => {
          const Icon = sequence.icon;
          const running = sequence.id === activeSequenceId && requestState !== "error";

          return (
            <Card
              className={`min-h-72 p-8 ${running ? "outline outline-2 outline-offset-4 outline-[#003C69]" : ""}`}
              key={sequence.id}
            >
              <div className="mb-8 flex items-start justify-between gap-4">
                <span className={`grid h-16 w-16 place-items-center rounded-xl ${running ? "bg-[#00548F] text-white" : "bg-[#E6E6E6] text-black"}`}>
                  <Icon className="h-8 w-8" />
                </span>
                <span className="rounded-lg bg-[#E8EAED] px-5 py-3 font-mono text-base uppercase tracking-[0.12em] text-[#29303A]">
                  {running ? "Running" : "Idle"}
                </span>
              </div>
              <h2 className="text-3xl font-black tracking-normal text-black">{sequence.title}</h2>
              <p className="mt-4 min-h-16 max-w-xl text-xl leading-8 text-[#303843]">
                {sequence.description}
              </p>
              <div className="mt-7 flex items-center justify-between border-t border-[#CAD1DA] pt-6">
                <p className="font-mono text-xl">ETA: {sequence.estimate}</p>
                <button
                  className={`grid h-16 w-16 place-items-center rounded-full text-white shadow-lg ${running ? "bg-[#C7181D]" : "bg-[#00751A]"}`}
                  onClick={() => void (running ? cancelTask() : runSequence(sequence.id))}
                  type="button"
                >
                  {running ? <Square className="h-6 w-6" /> : <Play className="h-6 w-6 fill-current" />}
                </button>
              </div>
            </Card>
          );
        })}
      </section>

      <footer className="fixed inset-x-0 bottom-0 z-30 border-t border-[#C4CBD5] bg-white px-5 py-5 shadow-[0_-4px_16px_rgba(20,30,45,0.06)] md:px-9">
        <div className="mx-auto grid max-w-[1920px] gap-5 lg:grid-cols-[320px_1fr_420px] lg:items-center">
          <div className="flex items-center gap-5">
            <span className="grid h-16 w-16 place-items-center rounded-full bg-[#00548F] text-white">
              {ActiveIcon ? <ActiveIcon className="h-8 w-8" /> : null}
            </span>
            <div>
              <p className="text-sm font-black uppercase tracking-[0.12em] text-[#003C69]">
                Active Sequence
              </p>
              <p className="text-2xl font-black">{active?.title ?? "None"}</p>
            </div>
          </div>
          <div>
            <div className="mb-3 flex items-center justify-between gap-4 text-lg">
              <p>{active ? taskStatus?.message || message : "Waiting for request"}</p>
              <p className="font-black text-[#003C69]">{active ? sequenceProgress : 0}%</p>
            </div>
            <ProgressBar value={active ? sequenceProgress : 0} />
          </div>
          <div className="flex gap-5 lg:justify-end">
            {isPaused ? (
              <IndustrialButton
                className="min-w-40"
                onClick={() => void resumeTask()}
                disabled={estopActive}
                tone="primary"
              >
                <Play className="h-5 w-5" /> Resume
              </IndustrialButton>
            ) : (
              <IndustrialButton
                className="min-w-40"
                onClick={() => void pauseTask()}
                disabled={!activeSequenceId || estopActive}
                tone="secondary"
              >
                <Pause className="h-5 w-5" /> Pause
              </IndustrialButton>
            )}
            <IndustrialButton className="min-w-40" onClick={() => void cancelTask()} disabled={!activeSequenceId && !isPaused && !estopActive} tone="danger">
              <Square className="h-5 w-5" /> Abort
            </IndustrialButton>
          </div>
        </div>
      </footer>
    </div>
  );
}
