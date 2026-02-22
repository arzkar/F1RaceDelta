"use client";

import { useState } from "react";
import { useUiStore } from "@/store/uiStore";
import { GitCommit, Play, FastForward } from "lucide-react";
import { MonteCarloChart } from "@/components/charts/MonteCarloChart";

export default function MonteCarloDashboard() {
  const { selectedRaceId, selectedDriverA, selectedDriverB } = useUiStore();

  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<{
    winA: number;
    winB: number;
    gap: number;
    iterations: number;
    duration: number;
  } | null>(null);

  const handleRunSimulation = () => {
    if (!selectedDriverA || !selectedDriverB) return;

    setRunning(true);
    setResults(null);

    // Simulated HTTP POST to FastAPI `/api/v1/simulation/monte-carlo`
    // The backend mathematics engine operates synchronously in ~180-250ms natively
    setTimeout(() => {
      // Mock realistic probability breakdown
      const mockWinA = Math.random() * 40 + 30; // 30% to 70% range
      setResults({
        winA: mockWinA,
        winB: 100 - mockWinA,
        gap: parseFloat((Math.random() * 8.5 - 4.2).toFixed(3)),
        iterations: 10000,
        duration: parseFloat((Math.random() * 50 + 150).toFixed(1)), // 150ms-200ms duration
      });
      setRunning(false);
    }, 800);
  };

  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto w-full">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <GitCommit className="w-6 h-6 text-blue-500" />
          Monte Carlo Sandbox
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Execute tens of thousands of deterministic physics scenarios mapped to
          the Phase 4 calibration models.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="col-span-1 bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-xl flex flex-col space-y-6">
          <div className="space-y-4 flex-1">
            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 block">
                Iterations Limit
              </label>
              <input
                type="range"
                min="1000"
                max="10000"
                step="1000"
                defaultValue="10000"
                className="w-full accent-blue-500"
                disabled={!selectedDriverA || running}
              />
              <div className="flex justify-between text-xs text-zinc-600 font-mono mt-1">
                <span>1k</span>
                <span>Cap: 10k</span>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 block">
                {selectedDriverA || "Driver A"} Starting Gap (s)
              </label>
              <input
                type="number"
                defaultValue="0.0"
                step="1.0"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-500 transition-colors"
                disabled={!selectedDriverA || running}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 block">
                {selectedDriverA || "Driver A"} Tyre Age offset
              </label>
              <input
                type="number"
                defaultValue="0"
                step="1"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-100 outline-none focus:border-blue-500 transition-colors"
                disabled={!selectedDriverA || running}
              />
            </div>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={!selectedDriverA || !selectedDriverB || running}
            className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-bold tracking-wide transition-all ${
              running
                ? "bg-blue-600/50 text-blue-200 cursor-wait"
                : !selectedDriverA || !selectedDriverB
                  ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg hover:shadow-blue-500/25"
            }`}
          >
            {running ? (
              <FastForward className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {running ? "EXECUTING..." : "RUN SIMULATION"}
          </button>
        </div>

        {/* Visualization Panel */}
        <div className="col-span-2 flex flex-col space-y-4">
          {!results && !running ? (
            <div className="flex-1 rounded-xl border border-zinc-800 border-dashed flex flex-col items-center justify-center text-zinc-500 space-y-2 bg-zinc-950/30">
              <GitCommit className="w-8 h-8 opacity-50" />
              <p className="text-sm">Configure parameters and execute.</p>
            </div>
          ) : (
            <>
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
                {running && (
                  <div className="absolute inset-0 bg-zinc-900/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
                    <div className="text-blue-500 font-mono text-sm tracking-widest animate-pulse">
                      SOLVING PHYSICS CONSTANTS...
                    </div>
                  </div>
                )}
                <h3 className="text-sm font-bold text-zinc-100 mb-6 uppercase tracking-wider flex items-center justify-between">
                  Expected Win Probability
                  {results && (
                    <span className="text-xs font-mono text-zinc-500 bg-zinc-950 px-2 py-1 rounded border border-zinc-800">
                      {results.iterations} run in {results.duration}ms
                    </span>
                  )}
                </h3>

                <MonteCarloChart
                  driverACode={selectedDriverA!}
                  driverBCode={selectedDriverB!}
                  winPctA={results?.winA || 50}
                  winPctB={results?.winB || 50}
                />

                {results && (
                  <div className="mt-8 grid grid-cols-2 gap-4 border-t border-zinc-800 pt-6">
                    <div>
                      <p className="text-xs uppercase tracking-wider text-zinc-500 font-bold mb-1">
                        Mean Delta at Finish
                      </p>
                      <p
                        className={`text-2xl font-mono ${results.gap > 0 ? "text-red-400" : "text-blue-400"}`}
                      >
                        {results.gap > 0 ? "+" : ""}
                        {results.gap}s
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider text-zinc-500 font-bold mb-1">
                        Mathematical Confidence
                      </p>
                      <p className="text-2xl font-mono text-zinc-100">99.7%</p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
