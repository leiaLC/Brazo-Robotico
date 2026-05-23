"use client";

import {
  BatteryCharging,
  Link2,
  RadioTower,
  RotateCcw,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { navItems, systemStatus } from "@/lib/mock-data";

type SafetyRequestState = "idle" | "stopping" | "resuming" | "error";

type TaskStatus = {
  mode: string;
  message: string;
  estop_active: boolean;
};

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function getTaskStatusWebSocketUrl(backendUrl: string) {
  const url = new URL(backendUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/task-status";
  url.search = "";
  return url.toString();
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [safetyRequestState, setSafetyRequestState] = useState<SafetyRequestState>("idle");
  const [statusSocketState, setStatusSocketState] = useState<
    "connecting" | "connected" | "disconnected" | "error"
  >("connecting");
  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? getDefaultBackendUrl(),
    [],
  );

  const estopActive = Boolean(taskStatus?.estop_active);
  const safetyBusy = safetyRequestState === "stopping" || safetyRequestState === "resuming";

  useEffect(() => {
    const socket = new WebSocket(getTaskStatusWebSocketUrl(backendUrl));

    socket.addEventListener("open", () => setStatusSocketState("connected"));
    socket.addEventListener("error", () => setStatusSocketState("error"));
    socket.addEventListener("close", () => setStatusSocketState("disconnected"));
    socket.addEventListener("message", (event) => {
      const nextStatus = JSON.parse(event.data) as TaskStatus;
      setTaskStatus(nextStatus);
      setSafetyRequestState("idle");
    });

    return () => {
      socket.close();
    };
  }, [backendUrl]);

  async function sendEmergencyStop() {
    if (safetyBusy) {
      return;
    }

    setSafetyRequestState("stopping");
    try {
      const response = await fetch(`${backendUrl}/task/estop`, { method: "POST" });
      if (response.ok) {
        setTaskStatus((current) =>
          current
            ? { ...current, mode: "ESTOP", message: "Emergency stop sent", estop_active: true }
            : { mode: "ESTOP", message: "Emergency stop sent", estop_active: true },
        );
      }
      setSafetyRequestState(response.ok ? "idle" : "error");
    } catch {
      setSafetyRequestState("error");
    }
  }

  async function sendResume() {
    if (safetyBusy) {
      return;
    }

    setSafetyRequestState("resuming");
    try {
      const response = await fetch(`${backendUrl}/task/resume`, { method: "POST" });
      if (response.ok) {
        setTaskStatus((current) =>
          current
            ? { ...current, estop_active: false, mode: "IDLE", message: "Resume sent" }
            : current,
        );
      }
      setSafetyRequestState(response.ok ? "idle" : "error");
    } catch {
      setSafetyRequestState("error");
    }
  }

  const safetyButtonLabel = (() => {
    if (safetyRequestState === "stopping") {
      return "Stopping...";
    }
    if (safetyRequestState === "resuming") {
      return "Resuming...";
    }
    if (estopActive) {
      return "Resume System";
    }
    return "Emergency Stop";
  })();

  const SafetyIcon = estopActive ? RotateCcw : TriangleAlert;

  return (
    <div className="min-h-screen bg-[#F6F7F8] text-[#111820]">
      <header className="sticky top-0 z-40 flex min-h-20 items-center border-b border-[#C4CBD5] bg-white/95 px-5 shadow-[0_1px_0_rgba(20,30,45,0.04)] backdrop-blur md:px-8">
        <Link
          href="/"
          className="mr-5 flex min-w-fit items-center gap-3 text-xl font-black tracking-normal text-[#003C69] lg:text-2xl"
        >
          <span className="grid h-9 w-9 place-items-center rounded-lg border-2 border-[#003C69] font-black">
            Y
          </span>
          {systemStatus.robot}
        </Link>

        <nav className="flex min-w-0 flex-1 items-stretch gap-1 overflow-x-auto px-1">
          {navItems.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`relative flex min-h-20 shrink-0 items-center px-4 text-base font-semibold transition lg:px-6 ${
                  active ? "text-[#003C69]" : "text-[#1F2730] hover:text-[#003C69]"
                }`}
                href={item.href}
                key={item.href}
              >
                {item.label}
                {active ? (
                  <span className="absolute inset-x-3 bottom-0 h-1 rounded-t bg-[#003C69]" />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-5 px-4 text-[#003C69] xl:flex">
          <Link2 className="h-5 w-5" />
          <BatteryCharging className="h-6 w-6" />
          <RadioTower className="h-5 w-5" />
          {estopActive ? <ShieldAlert className="h-6 w-6 text-[#C7181D]" /> : null}
        </div>

        <button
          aria-label={estopActive ? "Resume System" : "Emergency Stop"}
          className={`ml-3 flex min-h-16 shrink-0 items-center justify-center gap-3 rounded-lg border px-5 text-base font-black uppercase tracking-normal text-white shadow-[0_4px_10px_rgba(120,0,0,0.18)] transition disabled:cursor-wait disabled:opacity-70 lg:min-w-80 lg:text-2xl ${
            estopActive
              ? "border-[#006315] bg-[#00751A] hover:bg-[#006315]"
              : "border-[#9E1013] bg-[#C7181D] hover:bg-[#A41114]"
          }`}
          disabled={safetyBusy}
          onClick={() => void (estopActive ? sendResume() : sendEmergencyStop())}
          title={taskStatus?.message ?? `Task status: ${statusSocketState}`}
          type="button"
        >
          <SafetyIcon className="hidden h-8 w-8 lg:block" />
          {safetyButtonLabel}
        </button>
      </header>
      <main className="mx-auto w-full max-w-[1920px] px-5 py-8 md:px-9">{children}</main>
    </div>
  );
}
