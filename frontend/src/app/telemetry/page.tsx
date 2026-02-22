"use client";

import { useState, useEffect } from "react";
import { useUiStore } from "@/store/uiStore";
import { useTelemetry } from "@/hooks/useTelemetryWorker";
import { TelemetryChart } from "@/components/charts/TelemetryChart";
import { Activity } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

/** Fetch a presigned R2 URL for a given race + driver code */
function useTelemetryUrl(raceId: string | null, driverCode: string | null) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!raceId || !driverCode) {
      setUrl(null);
      return;
    }

    fetch(`${API_BASE}/telemetry/${raceId}/${driverCode}`)
      .then((res) => {
        if (res.status === 204) throw new Error("No telemetry available.");
        if (!res.ok) throw new Error("API Error");
        return res.json();
      })
      .then((data) => setUrl(data.url))
      .catch(() => setUrl(null));
  }, [raceId, driverCode]);

  return url;
}

export default function TelemetryDashboard() {
  const { selectedRaceId, selectedDriverA, selectedDriverB } = useUiStore();

  // Fetch presigned URLs for both drivers independently
  const urlA = useTelemetryUrl(selectedRaceId, selectedDriverA);
  const urlB = useTelemetryUrl(selectedRaceId, selectedDriverB);

  // Decode both Parquet streams via parallel Web Workers
  const { data: dataA, loading: loadingA, error: errorA } = useTelemetry(urlA);
  const { data: dataB, loading: loadingB, error: errorB } = useTelemetry(urlB);

  const isLoading = loadingA || loadingB;
  const hasDrivers = selectedRaceId && selectedDriverA;

  return (
    <div className="flex flex-col h-full space-y-4 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" />
            Live Telemetry Stream
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            {hasDrivers
              ? `Comparing ${selectedDriverA}${selectedDriverB ? ` vs ${selectedDriverB}` : ""} · ${selectedRaceId?.substring(0, 8).toUpperCase()}`
              : "Select a Race and Driver Configuration from the Topbar to begin decoding traces."}
          </p>
        </div>

        {isLoading && (
          <div className="flex items-center gap-3 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-full border border-blue-500/20">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider">
              Decoding Parquet WASM
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl relative">
        {!hasDrivers ? (
          <div className="absolute inset-0 flex items-center justify-center text-zinc-500 font-mono text-sm">
            Waiting for SaaS Configuration Parameters...
          </div>
        ) : errorA ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-950/20 text-red-400 p-8 text-center space-y-4">
            <span className="font-bold tracking-wide">
              Storage Gateway Disconnected
            </span>
            <code className="text-xs text-red-300 bg-red-950/50 p-4 rounded-lg border border-red-900/50 max-w-2xl overflow-auto">
              {errorA}
            </code>
          </div>
        ) : dataA ? (
          <TelemetryChart
            dataA={dataA}
            dataB={dataB ?? undefined}
            driverCodeA={selectedDriverA}
            driverCodeB={selectedDriverB ?? undefined}
            errorB={errorB ?? undefined}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Empty state while loading */}
          </div>
        )}
      </div>
    </div>
  );
}
