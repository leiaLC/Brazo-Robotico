import { Circle } from "lucide-react";
import { TeleopControlPanel } from "@/components/teleop-control-panel";
import { TeleopViewport } from "@/components/robot-visuals";
import { jointControls } from "@/lib/mock-data";

export default function TeleoperationPage() {
  return (
    <div className="-mx-5 -mb-8 -mt-8 grid min-h-[calc(100vh-5rem)] md:-mx-9 xl:grid-cols-[720px_1fr]">
      <TeleopControlPanel joints={jointControls} />
      <section className="relative">
        <TeleopViewport />
        <div className="absolute left-8 top-8 hidden rounded-lg bg-white/90 px-4 py-3 font-mono text-xs uppercase tracking-[0.12em] text-white/70 xl:block">
          <Circle className="h-3 w-3 fill-[#D8FFFF] text-[#D8FFFF]" />
        </div>
      </section>
    </div>
  );
}
