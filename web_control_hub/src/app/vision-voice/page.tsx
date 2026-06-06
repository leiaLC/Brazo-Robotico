"use client";

import { List, Mic, MicOff } from "lucide-react";
import { useEffect, useState } from "react";
import { VisionCameraPanel } from "@/components/robot-visuals";
import { Card, IndustrialButton, PageTitle, StatusPill } from "@/components/ui";

type VoiceRequestState = "idle" | "sending" | "sent" | "error";
type VoiceStatus =
  | "unknown"
  | "idle"
  | "prompting_password"
  | "listening_password"
  | "password_rejected"
  | "prompting_command"
  | "listening_command"
  | "clarification_needed"
  | "transcribing"
  | "interpreting"
  | "processing"
  | "publishing"
  | "published"
  | "no_audio"
  | "done"
  | "error";
type VoiceEvent = {
  type:
    | "cycle_started"
    | "cycle_finished"
    | "heard"
    | "heard_text"
    | "published"
    | "rejected"
    | "clarification"
    | "no_audio"
    | "message";
  text: string;
  confidence?: number | null;
  stamp?: number;
};

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function getVoiceStatusWebSocketUrl(backendUrl: string) {
  const url = new URL(backendUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/voice-status";
  url.search = "";
  return url.toString();
}

function getVoiceEventsWebSocketUrl(backendUrl: string) {
  const url = new URL(backendUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/voice-events";
  url.search = "";
  return url.toString();
}

function isVoiceActive(status: VoiceStatus) {
  return [
    "prompting_password",
    "listening_password",
    "prompting_command",
    "listening_command",
    "transcribing",
    "interpreting",
    "processing",
    "publishing",
    "published",
  ].includes(status);
}

function isVoiceListening(status: VoiceStatus) {
  return ["listening_password", "listening_command"].includes(status);
}

function messageForVoiceStatus(status: VoiceStatus) {
  const messages: Record<VoiceStatus, string> = {
    unknown: "Waiting for voice status...",
    idle: "System is not listening.",
    prompting_password: "Robot is asking for the password. Wait for the cue to finish.",
    listening_password: "Speak now: say the password.",
    password_rejected: "Password rejected.",
    prompting_command: "Robot is asking for the command. Wait for the cue to finish.",
    listening_command: "Speak now: say the robot command.",
    clarification_needed: "I need one more detail. Try one of the suggested commands.",
    transcribing: "Transcribing what you said...",
    interpreting: "Interpreting command...",
    processing: "Preparing command for ROS...",
    publishing: "Sending command to the robot task system...",
    published: "Command sent.",
    no_audio: "No speech detected. Try again.",
    done: "Voice cycle complete.",
    error: "Voice cycle ended with an error.",
  };
  return messages[status];
}

function formatVoiceTime(stamp?: number) {
  const date = stamp ? new Date(stamp * 1000) : new Date();
  return date.toLocaleTimeString("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatVoiceConfidence(confidence?: number | null) {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) {
    return "--";
  }
  const normalized = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.round(normalized)}%`;
}

function labelForVoiceEvent(event: VoiceEvent) {
  const labels: Record<VoiceEvent["type"], string> = {
    cycle_started: "Cycle",
    cycle_finished: "Done",
    heard: "Heard",
    heard_text: "Text",
    published: "Published",
    rejected: "Rejected",
    clarification: "Clarify",
    no_audio: "No audio",
    message: "Message",
  };
  return labels[event.type] ?? "Message";
}

function keepLatestVoiceEvents(events: VoiceEvent[]) {
  return events.slice(-25);
}

function isVoiceEvent(payload: VoiceEvent | { events?: VoiceEvent[] }): payload is VoiceEvent {
  return "type" in payload && "text" in payload;
}

export default function VisionVoicePage() {
  const [backendUrl] = useState(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? getDefaultBackendUrl(),
  );
  const [voiceRequestState, setVoiceRequestState] = useState<VoiceRequestState>("idle");
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("unknown");
  const [voiceMessage, setVoiceMessage] = useState("Waiting for voice status...");
  const [voiceEvents, setVoiceEvents] = useState<VoiceEvent[]>([]);
  const [suggestedCommands, setSuggestedCommands] = useState<string[]>([]);
  const [sessionStarted, setSessionStarted] = useState("--:--:--");
  const voiceRequested = isVoiceActive(voiceStatus);
  const voiceListening = isVoiceListening(voiceStatus);
  const voiceBusy = voiceRequestState === "sending";
  const voiceError = voiceRequestState === "error" || voiceStatus === "error";
  const VoiceIcon = voiceRequested ? Mic : MicOff;
  const visibleVoiceEvents = voiceEvents
    .slice(-8)
    .reverse();

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setSessionStarted(formatVoiceTime());
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    const socket = new WebSocket(getVoiceStatusWebSocketUrl(backendUrl));

    socket.addEventListener("message", (event) => {
      const next = JSON.parse(event.data) as { status?: VoiceStatus };
      const status = next.status ?? "unknown";
      setVoiceStatus(status);
      setVoiceMessage(messageForVoiceStatus(status));
      if (!isVoiceActive(status)) {
        setVoiceRequestState(status === "error" ? "error" : "idle");
      }
    });

    socket.addEventListener("error", () => {
      setVoiceStatus("unknown");
      setVoiceMessage("Voice status connection failed.");
    });

    return () => {
      socket.close();
    };
  }, [backendUrl]);

  useEffect(() => {
    let cancelled = false;

    async function loadVoiceSuggestions() {
      try {
        const response = await fetch(`${backendUrl}/voice/suggestions`);
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        const payload = (await response.json()) as { commands?: string[] };
        if (!cancelled) {
          setSuggestedCommands(payload.commands ?? []);
        }
      } catch {
        if (!cancelled) {
          setSuggestedCommands([]);
        }
      }
    }

    loadVoiceSuggestions();

    return () => {
      cancelled = true;
    };
  }, [backendUrl]);

  useEffect(() => {
    let cancelled = false;

    async function loadVoiceLog() {
      try {
        const response = await fetch(`${backendUrl}/voice/log`);
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        const payload = (await response.json()) as { events?: VoiceEvent[] };
        if (!cancelled) {
          setVoiceEvents(keepLatestVoiceEvents(payload.events ?? []));
        }
      } catch {
        if (!cancelled) {
          setVoiceEvents([]);
        }
      }
    }

    loadVoiceLog();

    return () => {
      cancelled = true;
    };
  }, [backendUrl]);

  useEffect(() => {
    const socket = new WebSocket(getVoiceEventsWebSocketUrl(backendUrl));

    socket.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data) as VoiceEvent | { events?: VoiceEvent[] };
      if ("events" in payload) {
        setVoiceEvents(keepLatestVoiceEvents(payload.events ?? []));
        return;
      }
      if (!isVoiceEvent(payload)) {
        return;
      }
      setVoiceEvents((current) => keepLatestVoiceEvents([...current, payload]));
    });

    socket.addEventListener("error", () => {
      const errorEvent: VoiceEvent = {
        type: "message",
        text: "Voice event connection failed.",
        confidence: null,
      };
      setVoiceEvents((current) => keepLatestVoiceEvents([...current, errorEvent]));
    });

    return () => {
      socket.close();
    };
  }, [backendUrl]);

  async function startVoiceListening() {
    setVoiceRequestState("sending");
    setVoiceMessage("Requesting voice listener...");

    try {
      const response = await fetch(`${backendUrl}/voice/start`, { method: "POST" });
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      setVoiceRequestState("sent");
      setVoiceMessage("Voice listener requested. Watch robot_speech logs.");
    } catch (error) {
      setVoiceRequestState("error");
      setVoiceMessage(error instanceof Error ? error.message : "Voice request failed.");
    }
  }

  return (
    <div className="space-y-7">
      <PageTitle
        action={
          <>
            <StatusPill tone="blue">Live</StatusPill>
            <StatusPill tone="gray">Detect: Active</StatusPill>
          </>
        }
        title="Vision and Voice"
      />

      <section className="grid gap-8 xl:grid-cols-[1fr_600px]">
        <VisionCameraPanel />
        <aside className="space-y-6">
          <h2 className="text-3xl font-black">Voice Command</h2>
          <Card className="p-9 text-center">
            <span
              className={`mx-auto grid h-28 w-28 place-items-center rounded-full ${
                voiceRequested ? "bg-[#DDFBDD]" : voiceError ? "bg-[#FDE2DE]" : "bg-[#E7E7E7]"
              }`}
            >
              <VoiceIcon className="h-12 w-12 text-[#29303A]" />
            </span>
            <h3 className="mt-8 text-2xl font-black">
              {voiceListening
                ? "Speak Now"
                : voiceRequested
                  ? "Voice Active"
                  : voiceError
                    ? "Voice Request Failed"
                    : "Voice Ready"}
            </h3>
            <p className="mt-3 text-lg text-[#29303A]">{voiceMessage}</p>
            <IndustrialButton
              className="mt-9 w-full"
              disabled={voiceBusy}
              onClick={startVoiceListening}
              tone={voiceListening ? "success" : "secondary"}
            >
              <Mic className="h-5 w-5" /> {voiceBusy ? "Requesting..." : "Start Voice Command"}
            </IndustrialButton>
          </Card>

          <Card className="min-h-96">
            <div className="flex items-center justify-between border-b border-[#CAD1DA] p-6">
              <h3 className="text-lg font-black tracking-normal">Command Log</h3>
              <List className="h-5 w-5" />
            </div>
            <div className="p-6">
              <p className="mb-4 font-mono text-sm text-[#6F7782]">Session Started: {sessionStarted}</p>
              <div className="divide-y divide-[#E3E7EC]">
                {visibleVoiceEvents.length === 0 ? (
                  <p className="py-8 text-sm text-[#6F7782]">No voice commands received yet.</p>
                ) : (
                  visibleVoiceEvents.map((item, index) => (
                    <div
                      className="grid grid-cols-[88px_1fr_80px_56px] gap-3 py-4"
                      key={`${item.type}-${item.stamp ?? index}-${item.text}`}
                    >
                      <p className="font-mono text-xs uppercase text-[#6F7782]">{labelForVoiceEvent(item)}</p>
                      <p className="text-lg text-[#29303A]">{item.text}</p>
                      <p className="font-mono text-sm text-[#7B838E]">{formatVoiceTime(item.stamp)}</p>
                      <p className="font-mono text-sm font-bold text-[#003C69]">
                        {formatVoiceConfidence(item.confidence)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="mb-4 text-sm font-black uppercase tracking-[0.12em] text-[#29303A]">
              Suggested Commands
            </h3>
            <div className="flex flex-wrap gap-3">
              {suggestedCommands.length === 0 ? (
                <p className="text-sm text-[#6F7782]">No suggested commands received yet.</p>
              ) : (
                suggestedCommands.map((command) => (
                  <button
                    className="rounded border border-[#D0D6DE] bg-[#F8F9FA] px-4 py-2 font-mono text-sm transition hover:border-[#003C69] hover:bg-[#EEF5FB]"
                    key={command}
                    type="button"
                  >
                    &quot;{command}&quot;
                  </button>
                ))
              )}
            </div>
          </Card>
        </aside>
      </section>
    </div>
  );
}
