"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useState, useEffect } from "react";
import {
  Activity,
  BarChart2,
  GitCommit,
  Database,
  LayoutDashboard,
  Sun,
  Moon,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Telemetry", href: "/telemetry", icon: Activity },
    { label: "Strategy", href: "/strategy", icon: BarChart2 },
    { label: "Monte Carlo", href: "/monte-carlo", icon: GitCommit },
    { label: "Models", href: "/models", icon: Database },
  ];

  return (
    <aside className="w-64 flex-shrink-0 bg-[var(--surface)] border-r border-[var(--border)] flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-[var(--border)]">
        <span className="text-xl font-bold tracking-tight flex items-center gap-2">
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
                  ? "bg-[var(--panel-hover)] text-[var(--fg)]"
                  : "text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--panel)]"
              }`}
            >
              <item.icon
                className={`w-5 h-5 ${isActive ? "text-blue-500" : "text-[var(--muted)]"}`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--border)] space-y-3">
        {/* Theme Toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all bg-[var(--panel)] hover:bg-[var(--panel-hover)] text-[var(--muted)] hover:text-[var(--fg)] border border-[var(--border)]"
          aria-label="Toggle theme"
        >
          {mounted ? (
            theme === "dark" ? (
              <>
                <Sun className="w-4 h-4" />
                Light Mode
              </>
            ) : (
              <>
                <Moon className="w-4 h-4" />
                Dark Mode
              </>
            )
          ) : (
            <span className="h-4" />
          )}
        </button>

        {/* Engine Status */}
        <div className="px-3 py-2 rounded bg-[var(--panel)] border border-[var(--border)] flex flex-col items-center justify-center">
          <span className="text-xs text-[var(--muted)] uppercase tracking-wide font-bold">
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
