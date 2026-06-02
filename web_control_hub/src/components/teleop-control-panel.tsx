"use client";

import { Layers3, Pause, RotateCcw, Send, SquareStack, Wifi, WifiOff } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Card, IndustrialButton, PageTitle, StatusPill } from "@/components/ui";
import type { JointControl } from "@/lib/mock-data";

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

const PUBLISH_INTERVAL_MS = 80;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

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
    url.pathname = "/ws/robot-state";
    url.search = "";
    return url.toString();
  } catch {
    return null;
  }
}

export function TeleopControlPanel({
  joints,
  onBackendUrlChange,
  onPreviewPositionsChange,
  onTeleopEnabledChange,
}: {
  joints: JointControl[];
  onBackendUrlChange?: (backendUrl: string) => void;
  onPreviewPositionsChange?: (positions: number[]) => void;
  onTeleopEnabledChange?: (enabled: boolean) => void;
}) {
  const initialDegrees = useMemo(() => joints.map((joint) => joint.value), [joints]);
  const [positions, setPositions] = useState(initialDegrees);
  const [enabled, setEnabled] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [lastPublish, setLastPublish] = useState("No commands sent");
  const [feedbackPositions, setFeedbackPositions] = useState<number[] | null>(null);
  const [feedbackCount, setFeedbackCount] = useState(0);
  // SSR-stable: sin window aqui; el valor basado en window.location se aplica
  // tras montar (ver useEffect mas abajo) para evitar el hydration mismatch.
  const [backendUrl, setBackendUrl] = useState(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? "",
  );
  const lastPublishRef = useRef(0);
  const publishCountRef = useRef(0);
  const positionsInitializedRef = useRef(false);

  useEffect(() => {
    onBackendUrlChange?.(backendUrl);
  }, [backendUrl, onBackendUrlChange]);

  useEffect(() => {
    onTeleopEnabledChange?.(enabled && connectionState === "connected");
  }, [connectionState, enabled, onTeleopEnabledChange]);

  useEffect(() => {
    onPreviewPositionsChange?.(positions);
  }, [onPreviewPositionsChange, positions]);

  useEffect(() => {
    const wsUrl = backendUrl ? getBackendWebSocketUrl(backendUrl) : null;
    if (!wsUrl) {
      return;
    }

    const socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => setConnectionState("connected"));
    socket.addEventListener("error", () => setConnectionState("error"));
    socket.addEventListener("close", () => {
      setConnectionState("disconnected");
      setEnabled(false);
    });
    socket.addEventListener("message", (event) => {
      const robotState = JSON.parse(event.data) as {
        state_count?: number;
        positions_deg?: number[] | null;
      };

      if (!robotState.positions_deg || robotState.positions_deg.length !== 7) {
        return;
      }

      setFeedbackCount(robotState.state_count ?? 0);
      setFeedbackPositions(robotState.positions_deg);
      if (!positionsInitializedRef.current) {
        setPositions(robotState.positions_deg);
        positionsInitializedRef.current = true;
      }
    });

    return () => {
      socket.close();
    };
  }, [backendUrl]);

  function updateBackendUrl(value: string) {
    setConnectionState("connecting");
    setEnabled(false);
    setBackendUrl(value);
  }

  async function setBackendTeleopEnabled(nextEnabled: boolean) {
    if (connectionState !== "connected") {
      return;
    }

    const endpoint = nextEnabled ? "/teleop/enable" : "/teleop/disable";
    const response = await fetch(`${backendUrl}${endpoint}`, { method: "POST" });

    if (!response.ok) {
      setConnectionState("error");
      return;
    }

    setEnabled(nextEnabled);
    if (nextEnabled && feedbackPositions) {
      setPositions(feedbackPositions);
      positionsInitializedRef.current = true;
    }
  }

  async function publishJointTargets(nextPositions: number[], eventTimeStamp: number, force = false) {
    if (!enabled || connectionState !== "connected") {
      return;
    }

    if (!force && eventTimeStamp - lastPublishRef.current < PUBLISH_INTERVAL_MS) {
      return;
    }

    lastPublishRef.current = eventTimeStamp;
    publishCountRef.current += 1;

    const response = await fetch(`${backendUrl}/teleop/joint-target`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ positions_deg: nextPositions }),
    });

    if (!response.ok) {
      setConnectionState("error");
      return;
    }

    setLastPublish(`command #${publishCountRef.current}`);
  }

  async function publishGripperCommand(command: "open" | "close") {
    if (!canCommand) {
      return;
    }

    publishCountRef.current += 1;
    const response = await fetch(`${backendUrl}/teleop/gripper`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
      setConnectionState("error");
      return;
    }

    setLastPublish(`${command} gripper #${publishCountRef.current}`);
  }

  function updateJoint(index: number, value: number) {
    const joint = joints[index];
    const nextPositions = [...positions];
    nextPositions[index] = clamp(value, joint.min, joint.max);
    setPositions(nextPositions);
  }

  function nudgeJoint(index: number, delta: number) {
    updateJoint(index, positions[index] + delta);
  }

  function syncCurrentPose() {
    setPositions(feedbackPositions ?? initialDegrees);
  }

  const connected = connectionState === "connected";
  const canCommand = connected && enabled;

  return (
    <aside className="border-r border-[#C4CBD5] bg-[#F7F8F9] px-5 py-8 md:px-9">
      <div className="mb-7">
        <PageTitle
          action={
            <StatusPill icon={connected ? Wifi : WifiOff} tone={connected ? "green" : "red"}>
              Backend {connectionState}
            </StatusPill>
          }
          subtitle="Manual articulation routed through the backend gateway, not direct ROS topics."
          title="Teleoperation"
        />
      </div>

      <Card className="mb-5 p-5">
        <label className="grid gap-2">
          <span className="text-xs font-black uppercase tracking-[0.12em] text-[#29303A]">
            Backend gateway URL
          </span>
          <input
            className="min-h-12 rounded border border-[#BFC7D2] bg-white px-4 font-mono text-sm outline-none focus:border-[#003C69] focus:ring-2 focus:ring-[#CFE1F6]"
            onChange={(event) => updateBackendUrl(event.target.value)}
            value={backendUrl}
          />
        </label>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <IndustrialButton
            className="w-full"
            disabled={!connected}
            onClick={() => void setBackendTeleopEnabled(!enabled)}
            tone={enabled ? "danger" : "primary"}
          >
            {enabled ? <Pause className="h-5 w-5" /> : <Send className="h-5 w-5" />}
            {enabled ? "Disable Teleop" : "Enable Teleop"}
          </IndustrialButton>
          <IndustrialButton
            className="w-full"
            disabled={!feedbackPositions}
            onClick={() => syncCurrentPose()}
            tone="secondary"
          >
            <RotateCcw className="h-5 w-5" /> Sync Current
          </IndustrialButton>
          <IndustrialButton
            className="w-full sm:col-span-2"
            disabled={!canCommand}
            onClick={(event) => void publishJointTargets(positions, event.timeStamp, true)}
            tone="success"
          >
            <Send className="h-5 w-5" /> Send Target
          </IndustrialButton>
        </div>

        <p className="mt-4 font-mono text-xs text-[#5F6874]">
          Gateway publishes RobotCommand to /robot_task/command | Units sent to API: degrees | Last publish:{" "}
          {lastPublish}
        </p>
        <p className="mt-2 font-mono text-xs text-[#5F6874]">
          Feedback frames: {feedbackCount} | Gateway reads ROS2 /joint_states
        </p>
      </Card>

      <div className="industrial-scrollbar max-h-[calc(100vh-31rem)] space-y-4 overflow-y-auto pr-1">
        {joints.map((joint, index) => (
          <Card className={`p-5 ${canCommand ? "" : "opacity-75"}`} key={joint.name}>
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="font-mono text-lg font-black tracking-normal text-black">
                  {joint.name}
                </h2>
                <p className="text-xs uppercase tracking-[0.12em] text-[#6F7782]">
                  {joint.rosName} | {joint.axis}
                </p>
                {feedbackPositions ? (
                  <p className="mt-1 font-mono text-xs text-[#00751A]">
                    actual {feedbackPositions[index].toFixed(1)} deg
                  </p>
                ) : null}
              </div>
              <div className="text-right">
                <p className="text-sm text-[#6F7782]">{joint.range}</p>
                <p className="mt-1 rounded border border-[#92C1FF] bg-[#E2F0FF] px-3 py-1 font-mono text-sm text-[#003C69]">
                  {positions[index] > 0 ? "+" : ""}
                  {positions[index].toFixed(1)} deg
                </p>
              </div>
            </div>
            <div className="grid grid-cols-[48px_1fr_48px] items-center gap-4">
              <button
                className="grid h-12 w-12 place-items-center rounded border border-[#BFC7D2] bg-[#F5F6F7] disabled:cursor-not-allowed"
                disabled={!canCommand}
                onClick={() => nudgeJoint(index, -1)}
                type="button"
              >
                -
              </button>
              <input
                aria-label={joint.name}
                className="h-6 w-full disabled:cursor-not-allowed"
                disabled={!canCommand}
                max={joint.max}
                min={joint.min}
                onChange={(event) =>
                  updateJoint(index, Number(event.target.value))
                }
                type="range"
                value={positions[index]}
              />
              <button
                className="grid h-12 w-12 place-items-center rounded border border-[#BFC7D2] bg-[#F5F6F7] disabled:cursor-not-allowed"
                disabled={!canCommand}
                onClick={() => nudgeJoint(index, 1)}
                type="button"
              >
                +
              </button>
            </div>
          </Card>
        ))}

        <Card className={`p-5 ${canCommand ? "" : "opacity-75"}`}>
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-mono text-lg font-black tracking-normal text-black">
                Gripper
              </h2>
              <p className="text-xs uppercase tracking-[0.12em] text-[#6F7782]">
                open_gripper | close_gripper
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <IndustrialButton
              className="w-full"
              disabled={!canCommand}
              onClick={() => void publishGripperCommand("open")}
              tone="secondary"
            >
              <Layers3 className="h-5 w-5" /> Open Gripper
            </IndustrialButton>
            <IndustrialButton
              className="w-full"
              disabled={!canCommand}
              onClick={() => void publishGripperCommand("close")}
              tone="secondary"
            >
              <SquareStack className="h-5 w-5" /> Close Gripper
            </IndustrialButton>
          </div>
        </Card>
      </div>
    </aside>
  );
}
