"use client";

import { LayoutDashboard } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <LayoutDashboard className="w-6 h-6 text-blue-500" />
          F1RaceDelta Dashboard
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Welcome to the F1 Strategy Monte Carlo Sandbox. Configure your target
          race above.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link
          href="/telemetry"
          className="group p-6 bg-zinc-900 border border-zinc-800 hover:border-blue-500/50 rounded-xl transition-all cursor-pointer shadow-lg hover:shadow-blue-500/10"
        >
          <h2 className="text-lg font-semibold text-zinc-200 group-hover:text-blue-400 transition-colors">
            Telemetry Analyzer
          </h2>
          <p className="text-xs text-zinc-500 mt-2 leading-relaxed">
            High-performance WebGL arrays decoding Cloudflare R2 Parquet files
            via WASM. Zero-copy ECharts natively plotting Speed, Throttle,
            Braking, and RPM.
          </p>
        </Link>

        {/* Placeholder cards for future phases */}
        <div className="opacity-50 p-6 bg-zinc-900 border border-zinc-800 border-dashed rounded-xl cursor-not-allowed">
          <h2 className="text-lg font-semibold text-zinc-400">
            Monte Carlo Strategy
          </h2>
          <p className="text-xs text-zinc-600 mt-2 leading-relaxed">
            Execute Head-to-Head 10k simulations bound to the deterministic
            Phase 4 DB parameters and physics bounds.
          </p>
        </div>
      </div>
    </div>
  );
}
