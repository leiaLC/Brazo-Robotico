"use client";

import {
  CheckCircle2,
  CircleX,
  RadioTower,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui";

type RequiredNodeStatus = {
  name: string;
  active: boolean;
};

type NodeHealthResponse = {
  checked_at: string;
  all_required_active: boolean;
  active_count: number;
  required_count: number;
  nodes: RequiredNodeStatus[];
};

const defaultRequiredNodes = [
  "robot_state_publisher",
  "move_group",
  "egm_bridge",
  "egm_moveit_executor",
  "gripper_node",
  "gripper_joint_state_publisher",
  "robot_task_tree",
  "voice_commander_node",
  "web_command_bridge",
  "gamepad_command_bridge",
];

const nodeDetails: Record<string, { label: string; detail: string }> = {
  robot_state_publisher: {
    label: "Robot State Publisher",
    detail: "Publica transformaciones y estado cinemático del robot.",
  },
  move_group: {
    label: "MoveIt Planning",
    detail: "Planifica trayectorias antes de enviarlas al brazo.",
  },
  egm_bridge: {
    label: "EGM Bridge",
    detail: "Mantiene la comunicación UDP con el controlador ABB.",
  },
  egm_moveit_executor: {
    label: "EGM MoveIt Executor",
    detail: "Ejecuta las trayectorias de MoveIt a través de EGM.",
  },
  gripper_node: {
    label: "Gripper",
    detail: "Gestiona los comandos del efector final por RWS.",
  },
  gripper_joint_state_publisher: {
    label: "Gripper Joint State",
    detail: "Publica el estado estimado de las articulaciones del gripper.",
  },
  robot_task_tree: {
    label: "Behavior Trees",
    detail: "Supervisa tareas, seguridad y decisiones de movimiento.",
  },
  voice_commander_node: {
    label: "Voice Commander",
    detail: "Procesa audio y texto desde robot_speech para generar comandos.",
  },
  web_command_bridge: {
    label: "Web Command Bridge",
    detail: "Convierte solicitudes del front en comandos comunes ROS2.",
  },
  gamepad_command_bridge: {
    label: "Gamepad Command Bridge",
    detail: "Integra la teleoperación desde el control físico.",
  },
};

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function getNodeDetails(name: string) {
  const shortName = name.split("/").filter(Boolean).at(-1) ?? name;
  return (
    nodeDetails[shortName] ?? {
      label: shortName
        .split("_")
        .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
        .join(" "),
      detail: "Nodo ROS2 requerido para la operación del sistema.",
    }
  );
}

export function RosNodeHealthPanel() {
  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? getDefaultBackendUrl(),
    [],
  );
  const [health, setHealth] = useState<NodeHealthResponse | null>(null);
  const [requestError, setRequestError] = useState(false);
  const [refreshing, setRefreshing] = useState(true);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setRefreshing(true);
    try {
      const response = await fetch(`${backendUrl}/robot/nodes`, {
        cache: "no-store",
        signal,
      });
      if (!response.ok) {
        throw new Error(`Node health request failed: ${response.status}`);
      }
      setHealth((await response.json()) as NodeHealthResponse);
      setRequestError(false);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setRequestError(true);
      }
    } finally {
      if (!signal?.aborted) {
        setRefreshing(false);
      }
    }
  }, [backendUrl]);

  useEffect(() => {
    const controller = new AbortController();
    const initialRefresh = window.setTimeout(() => void refresh(controller.signal), 0);
    const interval = window.setInterval(() => void refresh(controller.signal), 4000);

    return () => {
      controller.abort();
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
    };
  }, [refresh]);

  const nodes =
    health?.nodes ?? defaultRequiredNodes.map((name) => ({ name, active: false }));
  const allActive = Boolean(health?.all_required_active && !requestError);
  const checkedAt = health
    ? new Intl.DateTimeFormat("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(health.checked_at))
    : "Sin datos";

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-[#D7DDE5] bg-[#F9FBFD] p-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <RadioTower className="h-7 w-7 text-[#003C69]" />
            <h2 className="text-2xl font-black text-[#111820]">Estado de nodos ROS2</h2>
          </div>
          <p className="mt-2 text-base text-[#4C5663]">
            Confirmación en vivo de los nodos requeridos para la puesta en marcha.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-black uppercase tracking-[0.06em] ${
              requestError
                ? "border-[#C3CAD4] bg-[#E8EAED] text-[#29303A]"
                : allActive
                  ? "border-[#A6E7A5] bg-[#DDFBDD] text-[#006315]"
                  : "border-[#F3ACA6] bg-[#FDE2DE] text-[#A41114]"
            }`}
          >
            {requestError ? (
              <TriangleAlert className="h-4 w-4" />
            ) : allActive ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <CircleX className="h-4 w-4" />
            )}
            {requestError
              ? "Backend sin conexión"
              : `${health?.active_count ?? 0}/${health?.required_count ?? nodes.length} activos`}
          </span>
          <button
            aria-label="Actualizar estado de nodos ROS2"
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#BFC7D2] bg-white px-4 text-sm font-bold text-[#003C69] transition hover:bg-[#F0F5FA] disabled:cursor-wait disabled:opacity-60"
            disabled={refreshing}
            onClick={() => void refresh()}
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="grid gap-px bg-[#D7DDE5] md:grid-cols-2 xl:grid-cols-3">
        {nodes.map((node) => (
          <NodeStatusCard
            active={node.active}
            backendConnected={!requestError && Boolean(health)}
            key={node.name}
            name={node.name}
          />
        ))}
      </div>

      <div className="border-t border-[#D7DDE5] bg-white px-6 py-3 text-right text-sm text-[#5E6670]">
        Última consulta: <span className="font-mono font-bold">{checkedAt}</span>
      </div>
    </Card>
  );
}

function NodeStatusCard({
  name,
  active,
  backendConnected,
}: {
  name: string;
  active: boolean;
  backendConnected: boolean;
}) {
  const { label, detail } = getNodeDetails(name);
  const status = !backendConnected ? "Sin conexión" : active ? "Activo" : "Inactivo";
  const statusClasses = !backendConnected
    ? "border-[#C3CAD4] bg-[#E8EAED] text-[#29303A]"
    : active
      ? "border-[#A6E7A5] bg-[#DDFBDD] text-[#006315]"
      : "border-[#F3ACA6] bg-[#FDE2DE] text-[#A41114]";
  const StatusIcon = !backendConnected ? TriangleAlert : active ? CheckCircle2 : CircleX;

  return (
    <article className="flex min-h-44 flex-col justify-between bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-black text-[#111820]">{label}</h3>
          <p className="mt-1 font-mono text-sm text-[#5E6670]">/{name.replace(/^\/+/, "")}</p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-black uppercase tracking-[0.06em] ${statusClasses}`}
        >
          <StatusIcon className="h-3.5 w-3.5" />
          {status}
        </span>
      </div>
      <p className="mt-4 text-sm leading-5 text-[#4C5663]">{detail}</p>
    </article>
  );
}
