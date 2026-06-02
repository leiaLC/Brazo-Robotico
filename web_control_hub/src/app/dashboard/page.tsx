import { MoreVertical, ShieldCheck } from "lucide-react";
import { EnergyUsageChart } from "@/components/charts";
import { Card, MetricCard, PageTitle, ProgressBar, StatusPill } from "@/components/ui";
import { cycleDistribution, overviewMetrics, systemStatus } from "@/lib/mock-data";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageTitle
        action={
          <>
            <StatusPill tone="green">{systemStatus.mode}</StatusPill>
            <StatusPill icon={ShieldCheck} tone="blue">
              {systemStatus.fence}
            </StatusPill>
          </>
        }
        title="Dashboard"
      />

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-5">
        {overviewMetrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className="grid gap-8 xl:grid-cols-[1.35fr_0.95fr]">
        <Card className="p-7">
          <div className="mb-7 flex items-center justify-between gap-4">
            <h2 className="text-2xl font-black tracking-normal text-black">Energy Usage Trend</h2>
            <div className="flex rounded-sm text-sm font-bold">
              {["1H", "24H", "7D"].map((item) => (
                <button
                  className={`min-h-10 border border-[#C4CBD5] px-4 ${item === "24H" ? "bg-[#003C69] text-white" : "bg-white text-black"}`}
                  key={item}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <EnergyUsageChart />
        </Card>

        <Card className="p-7">
          <div className="mb-20 flex items-center justify-between gap-4">
            <h2 className="text-2xl font-black tracking-normal text-black">
              Cycle Time Distribution
            </h2>
            <MoreVertical className="h-6 w-6 text-[#29303A]" />
          </div>
          <div className="space-y-7">
            {cycleDistribution.map((item) => (
              <div className="grid grid-cols-[150px_1fr_48px] items-center gap-5" key={item.label}>
                <p
                  className={`text-right text-base ${item.label.startsWith("Fault") ? "text-[#C7181D]" : "text-[#111820]"}`}
                >
                  {item.label}
                </p>
                <ProgressBar tone="gray" value={100} />
                <p className="font-mono text-base text-[#5E6670]">{item.value}%</p>
                <div className="col-start-2 -mt-11">
                  <div className={`h-9 ${item.tone}`} style={{ width: `${item.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
