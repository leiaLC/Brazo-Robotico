import { ArrowRight, Bot, Database, Microchip, Wrench, Zap } from "lucide-react";
import { RobotHeroPanel } from "@/components/robot-visuals";
import { Card, MetricCard, PageTitle } from "@/components/ui";
import { controlCards, quickStart, systemStatus } from "@/lib/mock-data";

export default function ControlPage() {
  return (
    <div className="space-y-7">
      <PageTitle centered title="Control Panel" />

      <section className="grid gap-6 xl:grid-cols-[1fr_390px]">
        <RobotHeroPanel />
        <aside className="rounded-lg border border-[#003C69] bg-[#003C69] p-8 text-white shadow-[0_2px_8px_rgba(20,30,45,0.09)]">
          <Bot className="mb-7 h-12 w-12" />
          <h2 className="text-3xl font-black">Welcome Operator</h2>
          <p className="mt-4 text-lg leading-7 text-[#BFD5EF]">
            The ABB IRB14050 system is ready. Ensure safety protocols are met before
            initiating teleoperation or sequence execution.
          </p>
          <div className="mt-16 rounded-lg border border-white/20 bg-white/10 p-5">
            <h3 className="mb-5 text-sm font-black uppercase tracking-[0.1em]">Quick Start</h3>
            <ol className="space-y-4">
              {quickStart.map((item, index) => (
                <li className="flex gap-3 text-base" key={item}>
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#D6E7FF] font-black text-[#003C69]">
                    {index + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </section>

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {controlCards.map((card) => (
          <MetricCard key={card.label} {...card} />
        ))}
      </section>

      <Card className="grid gap-6 p-6 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_220px]">
        <InfoItem icon={Database} label="IP Address" value={systemStatus.ip} />
        <InfoItem icon={Microchip} label="Firmware Version" value={systemStatus.firmware} />
        <InfoItem icon={Wrench} label="Last Maintenance" value={systemStatus.maintenance} />
        <button
          className="flex min-h-16 items-center justify-center gap-3 rounded-lg text-base font-black text-[#003C69] hover:bg-[#F0F5FA]"
          type="button"
        >
          View Full Specs <ArrowRight className="h-5 w-5" />
        </button>
      </Card>
    </div>
  );
}

function InfoItem({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Zap;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-5 border-[#D7DDE5] xl:border-r">
      <span className="grid h-14 w-14 place-items-center rounded-full bg-[#E3E5E8]">
        <Icon className="h-6 w-6 text-[#29303A]" />
      </span>
      <div>
        <p className="text-base text-[#29303A]">{label}</p>
        <p className="font-mono text-lg font-bold text-black">{value}</p>
      </div>
    </div>
  );
}
