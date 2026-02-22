"use client";

import { useState, useEffect } from "react";
import { useUiStore } from "@/store/uiStore";
import { useTelemetry } from "@/hooks/useTelemetryWorker";
import { TelemetryChart } from "@/components/charts/TelemetryChart";
import { Activity } from "lucide-react";

export default function TelemetryDashboard() {
  const { selectedRaceId, selectedDriverA } = useUiStore();
  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);

  // Simulated API Call to the Phase 5 FastAPI Data Lake Router
  useEffect(() => {
    if (!selectedRaceId || !selectedDriverA) {
      setPresignedUrl(null);
      return;
    }

    // In a live environment, this hits: `/api/v1/telemetry/${selectedRaceId}/${selectedDriverA}`
    // and returns { url: "https://r2.cloudflare.com/..." }
    console.log(
      `Fetching fast, presigned telemetry URL for ${selectedDriverA} at ${selectedRaceId}...`,
    );

    // For visual demonstration, we simulate an API returning a valid url.
    // The worker will fail to fetch 'MOCK_URL' gracefully if executed without real data.
    setTimeout(() => {
      setPresignedUrl(`MOCK_URL_${selectedRaceId}_${selectedDriverA}`);
    }, 500);
  }, [selectedRaceId, selectedDriverA]);

  const { data: telemetryData, loading, error } = useTelemetry(presignedUrl);

  return (
    <div className="flex flex-col h-full space-y-4 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" />
            Live Telemetry Stream
          </h1>
          <p className="text-sm text-zinc-400 mt-1 placeholder-opacity-50">
            {selectedRaceId
              ? `Visualizing Driver Traces for ${selectedRaceId.toUpperCase()}`
              : "Select a Race and Driver Configuration from the Topbar to begin decoding traces."}
          </p>
        </div>

        {loading && (
          <div className="flex items-center gap-3 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-full border border-blue-500/20">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider">
              Decoding Parquet WASM
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl relative">
        {!selectedRaceId || !selectedDriverA ? (
          <div className="absolute inset-0 flex items-center justify-center text-zinc-500 font-mono text-sm">
            Waiting for SaaS Configuration Parameters...
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-950/20 text-red-400 p-8 text-center space-y-4">
            <span className="font-bold tracking-wide">
              Storage Gateway Disconnected
            </span>
            <code className="text-xs text-red-300 bg-red-950/50 p-4 rounded-lg border border-red-900/50 max-w-2xl overflow-auto">
              {error}
            </code>
          </div>
        ) : telemetryData ? (
          <TelemetryChart
            data={telemetryData}
            driverCode={selectedDriverA}
            compoundColor="#ef4444" // Default mock Soft Tyre
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
