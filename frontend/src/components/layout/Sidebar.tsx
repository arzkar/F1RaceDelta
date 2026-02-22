"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart2,
  GitCommit,
  Database,
  LayoutDashboard,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Telemetry", href: "/telemetry", icon: Activity },
    { label: "Strategy", href: "/strategy", icon: BarChart2 },
    { label: "Monte Carlo", href: "/monte-carlo", icon: GitCommit },
    { label: "Models", href: "/models", icon: Database },
  ];

  return (
    <aside className="w-64 flex-shrink-0 bg-zinc-950 border-r border-zinc-800 flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-zinc-800">
        <span className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse shadow-[0_0_10px_rgba(220,38,38,0.7)]" />
          F1RaceDelta
        </span>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50"
              }`}
            >
              <item.icon
                className={`w-5 h-5 ${isActive ? "text-blue-500" : "text-zinc-500"}`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-zinc-800">
        <div className="px-3 py-2 rounded bg-zinc-900 border border-zinc-800 flex flex-col items-center justify-center">
          <span className="text-xs text-zinc-500 uppercase tracking-wide font-bold">
            Engine Status
          </span>
          <span className="text-sm font-mono text-green-500 mt-1 flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" /> Online
          </span>
        </div>
      </div>
    </aside>
  );
}
