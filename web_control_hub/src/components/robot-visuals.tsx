import { Camera, Crosshair, Maximize, Minus, Plus, RotateCcw, ScanLine } from "lucide-react";
import { visionDetections } from "@/lib/mock-data";

export function RobotHeroPanel() {
  return (
    <div className="relative min-h-[520px] overflow-hidden rounded-lg border border-[#B8C2CD] bg-[#D4DEE2]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.2)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.24)_1px,transparent_1px)] bg-[size:80px_80px]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_35%_30%,rgba(255,255,255,0.9),rgba(255,255,255,0)_32%),linear-gradient(135deg,rgba(0,60,105,0.2),rgba(17,24,32,0.15))]" />
      <div className="absolute left-[16%] top-[8%] h-[72%] w-[26%] rotate-[12deg] rounded-[44%] border-[34px] border-[#EEF4F6] shadow-[inset_0_0_0_8px_#AAB8C0,0_22px_46px_rgba(15,25,35,0.18)]" />
      <div className="absolute left-[38%] top-[11%] h-24 w-52 -rotate-[7deg] rounded-full border-[26px] border-[#EEF4F6] bg-[#AEBCC4] shadow-[inset_0_0_0_7px_#73818A]" />
      <div className="absolute left-[45%] top-[26%] h-[38%] w-[18%] rotate-[23deg] rounded-full border-[30px] border-[#E9F0F2] bg-[#B7C4CB] shadow-[inset_0_0_0_8px_#7F8D95]" />
      <div className="absolute bottom-[6%] left-[36%] h-28 w-64 rounded-t-[80px] border-[24px] border-[#E9F0F2] bg-[#AEBBC2] shadow-[inset_0_0_0_8px_#73818A]" />
      <div className="absolute left-[55%] top-[18%] h-20 w-20 rounded-lg bg-[#27323A] shadow-lg" />
      <div className="absolute left-[58%] top-[28%] h-36 w-6 rounded-full bg-[#27323A]" />
      <div className="absolute bottom-10 left-10 rounded-lg border border-[#CBD2DA] bg-white/92 p-5 shadow-lg">
        <div className="mb-3 flex items-center gap-3 text-sm font-black uppercase tracking-[0.1em]">
          <span className="h-3 w-3 rounded-full bg-[#79EE81]" />
          System Online
        </div>
        <p className="font-mono text-lg">Uptime: 142h 31m</p>
      </div>
    </div>
  );
}

export function TeleopViewport() {
  return (
    <div className="relative min-h-[calc(100vh-8rem)] overflow-hidden bg-[#AEB7B9]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.19)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.19)_1px,transparent_1px)] bg-[size:72px_72px]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0),rgba(246,247,248,0.62))]" />
      <div className="absolute left-[19%] top-[18%] h-[16%] w-[28%] rotate-[18deg] rounded-full border-[10px] border-[#D8FFFF]/65 shadow-[0_0_30px_rgba(194,255,255,0.45)]" />
      <div className="absolute left-[39%] top-[12%] h-[14%] w-[16%] rotate-[18deg] rounded-full border-[10px] border-[#D8FFFF]/65" />
      <div className="absolute left-[51%] top-[25%] h-[42%] w-[16%] rotate-[17deg] rounded-full border-[10px] border-[#D8FFFF]/65" />
      <div className="absolute bottom-[13%] left-[48%] h-[18%] w-[36%] rounded-[50%] border-[10px] border-[#D8FFFF]/55" />
      <div className="absolute left-[18%] top-[47%] h-28 w-24 rounded-lg border-[8px] border-[#D8FFFF]/65" />
      <div className="absolute left-[54%] top-[9%] h-32 w-44 rounded-lg border-[8px] border-[#D8FFFF]/65" />
      <div className="absolute right-9 top-9 overflow-hidden rounded-lg border border-[#C1C9D3] bg-white shadow-lg">
        {[Plus, Minus, RotateCcw, Maximize].map((Icon, index) => (
          <button
            className="grid h-16 w-16 place-items-center border-b border-[#C1C9D3] last:border-b-0"
            key={index}
            type="button"
          >
            <Icon className="h-6 w-6" />
          </button>
        ))}
      </div>
      <div className="absolute bottom-8 left-10 flex flex-wrap gap-5">
        <Readout title="TCP Position (mm)" value="X: 345.2  Y: -12.4  Z: 450.0" />
        <Readout title="Collision Status" value="Clear" success />
      </div>
    </div>
  );
}

function Readout({ title, value, success = false }: { title: string; value: string; success?: boolean }) {
  return (
    <div className="rounded-lg border border-[#C2CAD6] bg-white/94 px-6 py-4 shadow-lg">
      <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#29303A]">{title}</p>
      <p className="mt-2 font-mono text-lg text-black">
        {success ? <span className="mr-2 text-[#00751A]">OK</span> : null}
        {value}
      </p>
    </div>
  );
}

export function VisionCameraPanel() {
  return (
    <div className="relative min-h-[620px] overflow-hidden rounded-lg border border-[#B8C2CD] bg-[#091D22] shadow-[0_2px_8px_rgba(20,30,45,0.08)]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(127,255,255,0.08)_1px,transparent_1px),linear-gradient(rgba(127,255,255,0.08)_1px,transparent_1px)] bg-[size:72px_72px]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_48%_48%,rgba(111,184,197,0.35),rgba(9,29,34,0.85)_58%),linear-gradient(180deg,rgba(0,60,105,0.35),rgba(0,0,0,0.25))]" />
      <div className="absolute left-[35%] top-[24%] h-[12%] w-[32%] rounded bg-[#A9BEC4]/30 blur-[1px]" />
      <div className="absolute left-[44%] top-[36%] h-[10%] w-[11%] rounded border-8 border-[#84969C]/50" />
      <div className="absolute left-[33%] top-[52%] h-[9%] w-[42%] rounded bg-[#87999E]/30" />
      <Crosshair className="absolute left-1/2 top-1/2 h-10 w-10 -translate-x-1/2 -translate-y-1/2 text-white/80" />
      {visionDetections.map((item) => (
        <div
          className="absolute border-2 border-[#9CF59D] bg-[#9CF59D]/6"
          key={item.label}
          style={{ left: item.x, top: item.y, width: item.w, height: item.h }}
        >
          <span className="absolute left-2 top-1 bg-[#DDFBDD] px-2 py-1 font-mono text-xs font-bold text-[#002204]">
            {item.label} {item.confidence}
          </span>
        </div>
      ))}
      <div className="absolute bottom-6 left-6 flex items-center gap-5 rounded-lg border border-[#C2CAD6] bg-white/95 px-5 py-3 font-mono text-sm">
        <span>FPS: 59.9</span>
        <span>LATENCY: 12ms</span>
        <span>RES: 1080p</span>
      </div>
      <div className="absolute right-6 top-6 flex items-center gap-3 text-white/80">
        <Camera className="h-5 w-5" />
        <ScanLine className="h-5 w-5" />
      </div>
    </div>
  );
}
