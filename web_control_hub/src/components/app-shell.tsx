"use client";

import { BatteryCharging, Link2, RadioTower, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems, systemStatus } from "@/lib/mock-data";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#F6F7F8] text-[#111820]">
      <header className="sticky top-0 z-40 flex min-h-20 items-center border-b border-[#C4CBD5] bg-white/95 px-5 shadow-[0_1px_0_rgba(20,30,45,0.04)] backdrop-blur md:px-8">
        <Link
          href="/"
          className="mr-5 flex min-w-fit items-center gap-3 text-xl font-black tracking-normal text-[#003C69] lg:text-2xl"
        >
          <span className="grid h-9 w-9 place-items-center rounded-lg border-2 border-[#003C69] font-black">
            Y
          </span>
          {systemStatus.robot}
        </Link>

        <nav className="flex min-w-0 flex-1 items-stretch gap-1 overflow-x-auto px-1">
          {navItems.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`relative flex min-h-20 shrink-0 items-center px-4 text-base font-semibold transition lg:px-6 ${
                  active ? "text-[#003C69]" : "text-[#1F2730] hover:text-[#003C69]"
                }`}
                href={item.href}
                key={item.href}
              >
                {item.label}
                {active ? (
                  <span className="absolute inset-x-3 bottom-0 h-1 rounded-t bg-[#003C69]" />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-5 px-4 text-[#003C69] xl:flex">
          <Link2 className="h-5 w-5" />
          <BatteryCharging className="h-6 w-6" />
          <RadioTower className="h-5 w-5" />
        </div>

        <button
          className="ml-3 flex min-h-16 shrink-0 items-center justify-center gap-3 rounded-lg border border-[#9E1013] bg-[#C7181D] px-5 text-base font-black uppercase tracking-normal text-white shadow-[0_4px_10px_rgba(120,0,0,0.18)] transition hover:bg-[#A41114] lg:min-w-80 lg:text-2xl"
          type="button"
        >
          <TriangleAlert className="hidden h-8 w-8 lg:block" />
          Emergency Stop
        </button>
      </header>
      <main className="mx-auto w-full max-w-[1920px] px-5 py-8 md:px-9">{children}</main>
    </div>
  );
}
