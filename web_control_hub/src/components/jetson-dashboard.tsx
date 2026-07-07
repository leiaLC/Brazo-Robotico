"use client";

import {
  Activity,
  Cpu,
  Database,
  Gauge,
  HardDrive,
  type LucideIcon,
  MemoryStick,
  RefreshCw,
  ShieldCheck,
  Thermometer,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PowerUsageChart, type PowerTrendPoint } from "@/components/charts";
import { Card, MetricCard, PageTitle, ProgressBar, StatusPill } from "@/components/ui";

type Tone = "blue" | "green" | "gray" | "red";

type MemoryMetrics = {
  total_mb: number;
  used_mb: number;
  available_mb: number;
  used_percent: number;
};

type DiskMetrics = {
  mount: string;
  total_gb: number;
  used_gb: number;
  available_gb: number;
  used_percent: number;
};

type CpuCoreMetric = {
  index: number;
  usage_percent: number;
  frequency_mhz: number | null;
};

type TemperatureMetric = {
  name: string;
  value_c: number;
};

type PowerRailMetric = {
  name: string;
  current_mw: number;
  average_mw: number | null;
};

type JetsonMetrics = {
  checked_at: string;
  source: string;
  model: string | null;
  power_mode: string | null;
  uptime_seconds: number;
  load_average: number[];
  cpu: CpuCoreMetric[];
  cpu_usage_percent: number | null;
  gpu_usage_percent: number | null;
  memory: MemoryMetrics;
  swap: MemoryMetrics;
  disk: DiskMetrics;
  temperatures: TemperatureMetric[];
  max_temperature_c: number | null;
  power_rails: PowerRailMetric[];
  total_power_mw: number | null;
  tegrastats_raw: string | null;
  warnings: string[];
};

type TaskStatus = {
  mode?: string;
  message?: string;
  robot_ready?: boolean;
  estop_active?: boolean;
  teleop_active?: boolean;
};

type NodeHealth = {
  all_required_active: boolean;
  active_count: number;
  required_count: number;
};

function getDefaultBackendUrl() {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function formatGbFromMb(value: number) {
  return `${(value / 1024).toFixed(1)} GB`;
}

function formatWatts(valueMw: number | null) {
  return valueMw === null ? "Sin datos" : `${(valueMw / 1000).toFixed(1)} W`;
}

function formatPercent(value: number | null) {
  return value === null ? "Sin datos" : `${Math.round(value)}%`;
}

function formatUptime(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function temperatureTone(value: number | null): Tone {
  if (value === null) {
    return "gray";
  }
  if (value >= 80) {
    return "red";
  }
  if (value >= 70) {
    return "blue";
  }
  return "green";
}

function usageTone(value: number | null): Tone {
  if (value === null) {
    return "gray";
  }
  if (value >= 90) {
    return "red";
  }
  if (value >= 75) {
    return "blue";
  }
  return "green";
}

function compactName(name: string) {
  return name.replace("-thermal", "").toUpperCase();
}

export function JetsonDashboard() {
  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL ?? getDefaultBackendUrl(),
    [],
  );
  const [metrics, setMetrics] = useState<JetsonMetrics | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [nodeHealth, setNodeHealth] = useState<NodeHealth | null>(null);
  const [powerTrend, setPowerTrend] = useState<PowerTrendPoint[]>([]);
  const [requestError, setRequestError] = useState(false);
  const [metricsError, setMetricsError] = useState("");
  const [refreshing, setRefreshing] = useState(true);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setRefreshing(true);
    try {
      const [metricsResponse, taskResponse, nodesResponse] = await Promise.all([
        fetch(`${backendUrl}/system/jetson`, { cache: "no-store", signal }),
        fetch(`${backendUrl}/robot/task-status`, { cache: "no-store", signal }),
        fetch(`${backendUrl}/robot/nodes`, { cache: "no-store", signal }),
      ]);

      let nextMetrics: JetsonMetrics | null = null;
      if (metricsResponse.ok) {
        nextMetrics = (await metricsResponse.json()) as JetsonMetrics;
        setMetrics(nextMetrics);
        setMetricsError("");
      } else {
        const body = await metricsResponse.json().catch(() => null);
        setMetrics(null);
        setMetricsError(
          typeof body?.detail === "string"
            ? body.detail
            : `Jetson metrics request failed: ${metricsResponse.status}`,
        );
      }

      setTaskStatus(taskResponse.ok ? ((await taskResponse.json()) as TaskStatus) : null);
      setNodeHealth(nodesResponse.ok ? ((await nodesResponse.json()) as NodeHealth) : null);
      setRequestError(false);

      if (nextMetrics?.total_power_mw !== null && nextMetrics?.total_power_mw !== undefined) {
        const time = new Intl.DateTimeFormat("es-MX", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }).format(new Date(nextMetrics.checked_at));
        const watts = Number((nextMetrics.total_power_mw / 1000).toFixed(2));
        setPowerTrend((current) => [...current.slice(-23), { time, watts }]);
      }
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

  const checkedAt = metrics
    ? new Intl.DateTimeFormat("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(metrics.checked_at))
    : "Sin datos";

  const rosTone: Tone = requestError
    ? "red"
    : nodeHealth?.all_required_active
      ? "green"
      : "gray";
  const rosLabel = requestError
    ? "Backend offline"
    : nodeHealth
      ? `${nodeHealth.active_count}/${nodeHealth.required_count} ROS2`
      : "ROS2 sin datos";
  const taskMode = taskStatus?.mode ?? "Modo desconocido";
  const topMetrics = metrics ? buildMetricCards(metrics) : [];

  return (
    <div className="space-y-8">
      <PageTitle
        action={
          <>
            <StatusPill tone={requestError || metricsError ? "red" : "green"}>
              {requestError ? "Backend offline" : metricsError ? "Jetson sin datos" : "Jetson live"}
            </StatusPill>
            <StatusPill icon={ShieldCheck} tone={rosTone}>
              {rosLabel}
            </StatusPill>
          </>
        }
        title="Dashboard"
      />

      {requestError || metricsError ? (
        <Card className="border-[#F3ACA6] bg-[#FDE2DE] p-5 text-[#A41114]">
          <p className="font-bold">
            {requestError ? "No se pudo leer el backend." : "No hay metricas frescas de la Jetson."}
          </p>
          <p className="mt-1 text-sm">
            {requestError
              ? `Verifica que FastAPI este corriendo en ${backendUrl}.`
              : metricsError}
          </p>
        </Card>
      ) : null}

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-5">
        {topMetrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
        {!metrics && !requestError && !metricsError
          ? Array.from({ length: 5 }).map((_, index) => (
              <Card className="min-h-40 animate-pulse bg-[#F4F6F8] p-6" key={index}>
                <div className="h-5 w-28 rounded bg-[#D7DDE5]" />
                <div className="mt-16 h-10 w-36 rounded bg-[#D7DDE5]" />
              </Card>
            ))
          : null}
      </section>

      <section className="grid gap-8 xl:grid-cols-[1.35fr_0.95fr]">
        <Card className="p-7">
          <div className="mb-7 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-black tracking-normal text-black">
                Power Draw Trend
              </h2>
              <p className="mt-1 text-sm text-[#5E6670]">
                Lecturas reales de VDD_IN durante esta sesion.
              </p>
            </div>
            <button
              aria-label="Actualizar metricas Jetson"
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[#BFC7D2] bg-white px-4 text-sm font-bold text-[#003C69] transition hover:bg-[#F0F5FA] disabled:cursor-wait disabled:opacity-60"
              disabled={refreshing}
              onClick={() => void refresh()}
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Actualizar
            </button>
          </div>
          {powerTrend.length > 0 ? (
            <PowerUsageChart data={powerTrend} />
          ) : (
            <div className="grid h-[420px] place-items-center border border-dashed border-[#C2CAD6] text-[#5E6670]">
              Esperando lectura de potencia VDD_IN
            </div>
          )}
        </Card>

        <Card className="p-7">
          <div className="mb-7">
            <h2 className="text-2xl font-black tracking-normal text-black">Runtime Status</h2>
            <p className="mt-1 text-sm text-[#5E6670]">
              Estado real consultado desde la Jetson y ROS2.
            </p>
          </div>
          <div className="space-y-6">
            <StatusRow icon={Gauge} label="Task mode" value={taskMode} />
            <StatusRow
              icon={ShieldCheck}
              label="Metrics source"
              value={metrics?.source ?? "Sin datos"}
            />
            <StatusRow
              icon={Activity}
              label="Uptime"
              value={metrics ? formatUptime(metrics.uptime_seconds) : "Sin datos"}
            />
            <StatusRow
              icon={Cpu}
              label="Load average"
              value={metrics ? metrics.load_average.join(" / ") : "Sin datos"}
            />
            <StatusRow
              icon={Database}
              label="Model"
              value={metrics?.model?.replace("NVIDIA ", "") ?? "Sin datos"}
            />
          </div>

          <div className="mt-8 space-y-5">
            <h3 className="text-sm font-black uppercase tracking-[0.08em] text-[#29303A]">
              Temperaturas
            </h3>
            {metrics?.temperatures.map((temperature) => (
              <SensorBar
                key={temperature.name}
                label={compactName(temperature.name)}
                tone={temperatureTone(temperature.value_c)}
                value={temperature.value_c}
                valueLabel={`${temperature.value_c.toFixed(1)} C`}
              />
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-8 xl:grid-cols-2">
        <Card className="p-7">
          <h2 className="mb-7 text-2xl font-black tracking-normal text-black">CPU Cores</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {metrics?.cpu.map((core) => (
              <SensorBar
                key={core.index}
                label={`CPU ${core.index}`}
                tone={usageTone(core.usage_percent)}
                value={core.usage_percent}
                valueLabel={`${core.usage_percent.toFixed(1)}%${
                  core.frequency_mhz ? ` @ ${Math.round(core.frequency_mhz)} MHz` : ""
                }`}
              />
            ))}
          </div>
        </Card>

        <Card className="p-7">
          <h2 className="mb-7 text-2xl font-black tracking-normal text-black">Power Rails</h2>
          <div className="space-y-4">
            {metrics?.power_rails.length ? (
              metrics.power_rails.map((rail) => (
                <div
                  className="flex min-h-14 items-center justify-between border-b border-[#D7DDE5] last:border-b-0"
                  key={rail.name}
                >
                  <span className="font-mono text-sm font-bold text-[#29303A]">{rail.name}</span>
                  <span className="font-mono text-lg font-bold text-black">
                    {formatWatts(rail.current_mw)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-[#5E6670]">Sin lectura de tegrastats para rieles de potencia.</p>
            )}
          </div>
          <div className="mt-6 border-t border-[#D7DDE5] pt-4 text-right text-sm text-[#5E6670]">
            Ultima lectura: <span className="font-mono font-bold">{checkedAt}</span>
          </div>
        </Card>
      </section>
    </div>
  );
}

function buildMetricCards(metrics: JetsonMetrics) {
  const memoryUsed = formatGbFromMb(metrics.memory.used_mb);
  const memoryTotal = formatGbFromMb(metrics.memory.total_mb);

  return [
    {
      label: "Max Temp",
      value:
        metrics.max_temperature_c === null
          ? "Sin datos"
          : `${metrics.max_temperature_c.toFixed(1)} C`,
      detail: metrics.max_temperature_c === null ? "No sensor" : "Thermal",
      tone: temperatureTone(metrics.max_temperature_c),
      icon: Thermometer,
    },
    {
      label: "RAM",
      value: `${memoryUsed}`,
      detail: `${memoryTotal} total`,
      tone: usageTone(metrics.memory.used_percent),
      icon: MemoryStick,
    },
    {
      label: "GPU Load",
      value: formatPercent(metrics.gpu_usage_percent),
      detail: "GR3D",
      tone: usageTone(metrics.gpu_usage_percent),
      icon: Gauge,
    },
    {
      label: "Power Draw",
      value: formatWatts(metrics.total_power_mw),
      detail: metrics.power_mode ?? "nvpmodel",
      tone: "blue" as Tone,
      icon: Zap,
    },
    {
      label: "Disk",
      value: `${metrics.disk.used_percent.toFixed(0)}%`,
      detail: `${metrics.disk.available_gb.toFixed(0)} GB free`,
      tone: usageTone(metrics.disk.used_percent),
      icon: HardDrive,
    },
  ];
}

function StatusRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[#D7DDE5] pb-4 last:border-b-0">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-[#E8EAED]">
          <Icon className="h-5 w-5 text-[#29303A]" />
        </span>
        <span className="text-sm font-black uppercase tracking-[0.08em] text-[#29303A]">
          {label}
        </span>
      </div>
      <span className="max-w-56 truncate text-right font-mono text-base font-bold text-black">
        {value}
      </span>
    </div>
  );
}

function SensorBar({
  label,
  value,
  valueLabel,
  tone,
}: {
  label: string;
  value: number;
  valueLabel: string;
  tone: Tone;
}) {
  return (
    <div className="grid grid-cols-[76px_1fr_104px] items-center gap-4">
      <span className="font-mono text-sm font-bold text-[#29303A]">{label}</span>
      <ProgressBar
        tone={tone === "red" ? "red" : tone === "green" ? "green" : "blue"}
        value={Math.min(value, 100)}
      />
      <span className="text-right font-mono text-sm text-[#5E6670]">{valueLabel}</span>
    </div>
  );
}
