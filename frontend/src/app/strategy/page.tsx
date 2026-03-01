"use client";

import { useState } from "react";
import { useUiStore } from "@/store/uiStore";
import { StrategyChart } from "@/components/charts/StrategyChart";
import { Plus, Trash2, Play, Loader2 } from "lucide-react";

interface StintConfig {
  compound: string;
  laps: number;
}

interface StrategyLap {
  lap_number: number;
  simulated_time_s: number;
  tyre_wear: number;
  fuel_mass_kg: number;
  compound: string;
}

interface StrategyResult {
  total_laps_simulated: number;
  race_total_laps: number;
  circuit: string;
  circuit_length_km: number;
  laps: StrategyLap[];
  pit_laps: number[];
}

const COMPOUNDS = ["SOFT", "MEDIUM", "HARD"];
const COMPOUND_COLORS: Record<string, string> = {
  SOFT: "#ef4444",
  MEDIUM: "#eab308",
  HARD: "#d4d4d8",
};

export default function StrategyPage() {
  const { selectedRaceId } = useUiStore();

  const [stints, setStints] = useState<StintConfig[]>([
    { compound: "MEDIUM", laps: 25 },
    { compound: "HARD", laps: 30 },
  ]);
  const [baselineLap, setBaselineLap] = useState(85.0);
  const [startingFuel, setStartingFuel] = useState(110.0);
  const [result, setResult] = useState<StrategyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalStintLaps = stints.reduce((sum, s) => sum + s.laps, 0);

  const addStint = () => {
    if (stints.length < 5) {
      setStints([...stints, { compound: "HARD", laps: 15 }]);
    }
  };

  const removeStint = (index: number) => {
    if (stints.length > 1) {
      setStints(stints.filter((_, i) => i !== index));
    }
  };

  const updateStint = (
    index: number,
    field: keyof StintConfig,
    value: string | number,
  ) => {
    const updated = [...stints];
    if (field === "laps") {
      updated[index] = {
        ...updated[index],
        laps: Math.max(1, Math.min(100, Number(value))),
      };
    } else if (field === "compound") {
      updated[index] = {
        ...updated[index],
        compound: value as string,
      };
    }
    setStints(updated);
  };

  const runSimulation = async () => {
    if (!selectedRaceId) {
      setError("Select a race from the top bar first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/simulation/strategy`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            race_id: selectedRaceId,
            baseline_lap_time_s: baselineLap,
            starting_fuel_kg: startingFuel,
            stints: stints.map((s) => ({ compound: s.compound, laps: s.laps })),
          }),
        },
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }

      const data: StrategyResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "bg-[var(--panel)] border border-[var(--border)] text-[var(--fg)] text-sm rounded-md px-3 py-1.5 focus:ring-1 focus:ring-blue-500 outline-none transition-all w-full";

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <span className="text-blue-500">⚙</span> Race Strategy Simulator
          </h1>
          <p className="text-sm text-[var(--muted)] mt-1">
            Configure pit strategy and simulate lap times with calibrated
            degradation models
          </p>
        </div>
        {result && (
          <div className="text-right text-sm text-[var(--muted)]">
            <div className="font-mono">
              {result.circuit} · {result.circuit_length_km} km
            </div>
            <div>
              {result.total_laps_simulated} / {result.race_total_laps} laps
              simulated
            </div>
          </div>
        )}
      </div>

      {/* Controls Row */}
      <div className="flex gap-4 items-start">
        {/* Stint Builder */}
        <div className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
              Stint Plan ({stints.length} stop{stints.length > 1 ? "s" : ""})
            </h2>
            <span className="text-xs font-mono text-[var(--muted)]">
              {totalStintLaps} laps total
            </span>
          </div>

          {/* Visual stint bar */}
          <div className="flex h-6 rounded-lg overflow-hidden border border-[var(--border)]">
            {stints.map((stint, i) => (
              <div
                key={i}
                className="flex items-center justify-center text-xs font-bold transition-all"
                style={{
                  width: `${(stint.laps / Math.max(totalStintLaps, 1)) * 100}%`,
                  backgroundColor: COMPOUND_COLORS[stint.compound] || "#71717a",
                  color: stint.compound === "HARD" ? "#18181b" : "#fff",
                  minWidth: "30px",
                }}
              >
                {stint.laps}L
              </div>
            ))}
          </div>

          {/* Stint rows */}
          {stints.map((stint, i) => (
            <div key={i} className="flex items-center gap-3">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{
                  backgroundColor: COMPOUND_COLORS[stint.compound] || "#71717a",
                }}
              />
              <select
                className={inputClass + " !w-28"}
                value={stint.compound}
                onChange={(e) => updateStint(i, "compound", e.target.value)}
              >
                {COMPOUNDS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <input
                type="number"
                className={inputClass + " !w-20 font-mono text-center"}
                value={stint.laps}
                onChange={(e) =>
                  updateStint(i, "laps", parseInt(e.target.value) || 1)
                }
                min={1}
                max={100}
              />
              <span className="text-xs text-[var(--muted)]">laps</span>
              <button
                onClick={() => removeStint(i)}
                disabled={stints.length <= 1}
                className="ml-auto p-1.5 rounded text-[var(--muted)] hover:text-red-400 hover:bg-red-400/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}

          <button
            onClick={addStint}
            disabled={stints.length >= 5}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium text-[var(--muted)] hover:text-[var(--fg)] border border-dashed border-[var(--border)] rounded-lg hover:border-blue-500/50 transition-all disabled:opacity-30"
          >
            <Plus className="w-3.5 h-3.5" /> Add Stint
          </button>
        </div>

        {/* Parameters + Run */}
        <div className="w-56 space-y-3">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4 space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
              Parameters
            </h2>
            <div>
              <label className="text-xs text-[var(--muted)] block mb-1">
                Baseline Lap (s)
              </label>
              <input
                type="number"
                className={inputClass + " font-mono"}
                value={baselineLap}
                onChange={(e) =>
                  setBaselineLap(parseFloat(e.target.value) || 85)
                }
                step={0.5}
                min={60}
                max={120}
              />
            </div>
            <div>
              <label className="text-xs text-[var(--muted)] block mb-1">
                Starting Fuel (kg)
              </label>
              <input
                type="number"
                className={inputClass + " font-mono"}
                value={startingFuel}
                onChange={(e) =>
                  setStartingFuel(parseFloat(e.target.value) || 110)
                }
                step={5}
                min={10}
                max={150}
              />
            </div>
          </div>

          <button
            onClick={runSimulation}
            disabled={loading || !selectedRaceId}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Simulating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" /> Run Strategy
              </>
            )}
          </button>

          {error && (
            <div className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Chart Area */}
      <div className="flex-1 min-h-0 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4">
        {result ? (
          <StrategyChart
            laps={result.laps}
            pitLaps={result.pit_laps}
            raceTotalLaps={result.race_total_laps}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-[var(--muted)] text-sm">
            {selectedRaceId
              ? "Configure your strategy above and click Run to simulate"
              : "Select a race from the top bar to get started"}
          </div>
        )}
      </div>
    </div>
  );
}
