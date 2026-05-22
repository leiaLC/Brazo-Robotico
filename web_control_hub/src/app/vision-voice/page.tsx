import { List, Mic, MicOff } from "lucide-react";
import { VisionCameraPanel } from "@/components/robot-visuals";
import { Card, IndustrialButton, PageTitle, StatusPill } from "@/components/ui";
import { suggestedVoiceCommands, voiceCommands } from "@/lib/mock-data";

export default function VisionVoicePage() {
  return (
    <div className="space-y-7">
      <PageTitle
        action={
          <>
            <StatusPill tone="blue">Live</StatusPill>
            <StatusPill tone="gray">Detect: Active</StatusPill>
          </>
        }
        title="Vision y Voz"
      />

      <section className="grid gap-8 xl:grid-cols-[1fr_600px]">
        <VisionCameraPanel />
        <aside className="space-y-6">
          <h2 className="text-3xl font-black">Voice Command</h2>
          <Card className="p-9 text-center">
            <span className="mx-auto grid h-28 w-28 place-items-center rounded-full bg-[#E7E7E7]">
              <MicOff className="h-12 w-12 text-[#29303A]" />
            </span>
            <h3 className="mt-8 text-2xl font-black">Voice Disabled</h3>
            <p className="mt-3 text-lg text-[#29303A]">System is not listening.</p>
            <IndustrialButton className="mt-9 w-full" tone="secondary">
              <Mic className="h-5 w-5" /> Enable Voice Commands
            </IndustrialButton>
          </Card>

          <Card className="min-h-96">
            <div className="flex items-center justify-between border-b border-[#CAD1DA] p-6">
              <h3 className="text-lg font-black tracking-normal">Command Log</h3>
              <List className="h-5 w-5" />
            </div>
            <div className="p-6">
              <p className="mb-4 font-mono text-sm text-[#6F7782]">Session Started: 14:32:01</p>
              <div className="divide-y divide-[#E3E7EC]">
                {voiceCommands.map((item) => (
                  <div className="grid grid-cols-[1fr_80px_56px] gap-3 py-4" key={item.command}>
                    <p className="text-lg text-[#29303A]">{item.command}</p>
                    <p className="font-mono text-sm text-[#7B838E]">{item.time}</p>
                    <p className="font-mono text-sm font-bold text-[#003C69]">{item.confidence}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="mb-4 text-sm font-black uppercase tracking-[0.12em] text-[#29303A]">
              Suggested Commands
            </h3>
            <div className="flex flex-wrap gap-3">
              {suggestedVoiceCommands.map((command) => (
                <button
                  className="rounded border border-[#D0D6DE] bg-[#F8F9FA] px-4 py-2 font-mono text-sm"
                  key={command}
                  type="button"
                >
                  &quot;{command}&quot;
                </button>
              ))}
            </div>
          </Card>
        </aside>
      </section>
    </div>
  );
}
