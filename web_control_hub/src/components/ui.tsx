import type { LucideIcon } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Tone = "blue" | "green" | "gray" | "red";

const toneClasses: Record<Tone, string> = {
  blue: "bg-[#D6E7FF] text-[#003C69] border-[#AFCBEF]",
  green: "bg-[#DDFBDD] text-[#006315] border-[#A6E7A5]",
  gray: "bg-[#E8EAED] text-[#29303A] border-[#C3CAD4]",
  red: "bg-[#FDE2DE] text-[#A41114] border-[#F3ACA6]",
};

export function PageTitle({
  title,
  subtitle,
  action,
  centered = false,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  centered?: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-3 ${centered ? "items-center text-center" : "lg:flex-row lg:items-end lg:justify-between"}`}
    >
      <div>
        <h1 className="text-[clamp(2.2rem,3.6vw,4.2rem)] font-black uppercase leading-none tracking-normal text-[#171A1D]">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-4 max-w-2xl text-lg text-[#38404A]">{subtitle}</p>
        ) : null}
      </div>
      {action ? <div className="flex shrink-0 items-center gap-3">{action}</div> : null}
    </div>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-lg border border-[#C2CAD6] bg-white shadow-[0_2px_8px_rgba(20,30,45,0.05)] ${className}`}
    >
      {children}
    </section>
  );
}

export function StatusPill({
  children,
  tone = "gray",
  icon,
}: {
  children: ReactNode;
  tone?: Tone;
  icon?: LucideIcon;
}) {
  const Icon = icon;

  return (
    <span
      className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-4 text-sm font-bold uppercase tracking-[0.08em] ${toneClasses[tone]}`}
    >
      {Icon ? <Icon className="h-4 w-4" /> : <span className="h-3 w-3 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  tone,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
  icon: LucideIcon;
}) {
  return (
    <Card className="flex min-h-40 flex-col justify-between p-6">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-sm font-extrabold uppercase tracking-[0.08em] text-[#29303A]">
          {label}
        </h3>
        <Icon className="h-6 w-6 text-[#68717E]" />
      </div>
      <div className="flex items-end justify-between gap-4">
        <p className="font-mono text-4xl font-medium tracking-normal text-black">{value}</p>
        <span className={`rounded border px-3 py-1 text-sm ${toneClasses[tone]}`}>{detail}</span>
      </div>
    </Card>
  );
}

export function ProgressBar({
  value,
  tone = "blue",
}: {
  value: number;
  tone?: "blue" | "green" | "red" | "gray";
}) {
  const fill = {
    blue: "bg-[#2F6F95]",
    green: "bg-[#8EF08C]",
    red: "bg-[#C7181D]",
    gray: "bg-[#747B86]",
  }[tone];

  return (
    <div className="h-4 overflow-hidden rounded-full bg-[#E9E9E9]">
      <div className={`h-full rounded-full ${fill}`} style={{ width: `${value}%` }} />
    </div>
  );
}

export function IndustrialButton({
  children,
  tone = "secondary",
  className = "",
  ...props
}: {
  children: ReactNode;
  tone?: "primary" | "secondary" | "danger" | "success";
  className?: string;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const classes = {
    primary: "border-[#003C69] bg-[#003C69] text-white hover:bg-[#00548F]",
    secondary: "border-[#BFC7D2] bg-[#E8EAED] text-[#111820] hover:bg-[#DDE1E6]",
    danger: "border-[#A41114] bg-[#C7181D] text-white hover:bg-[#A41114]",
    success: "border-[#006315] bg-[#00751A] text-white hover:bg-[#006315]",
  }[tone];

  return (
    <button
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border px-5 text-sm font-extrabold uppercase tracking-[0.06em] shadow-[0_2px_5px_rgba(20,30,45,0.12)] transition disabled:cursor-not-allowed disabled:opacity-55 ${classes} ${className}`}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}
