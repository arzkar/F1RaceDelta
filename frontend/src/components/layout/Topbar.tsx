"use client";

import { useUiStore } from "@/store/uiStore";

export function Topbar() {
  const {
    selectedSeason,
    selectedRaceId,
    selectedDriverA,
    selectedDriverB,
    setSeason,
    setRace,
    setDrivers,
  } = useUiStore();

  // Mock generic catalogs for Phase 6 visualization
  // In actual implementation, these would fetch from /api/v1/catalog
  const seasons = [2024, 2025];
  const races = [
    { id: "bahrain", name: "Bahrain GP" },
    { id: "monza", name: "Italian GP" },
  ];
  const drivers = [
    { code: "VER", name: "Max Verstappen" },
    { code: "NOR", name: "Lando Norris" },
  ];

  return (
    <header className="h-16 flex-shrink-0 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800 flex items-center justify-between px-6 sticky top-0 z-50">
      <div className="flex items-center gap-4">
        {/* Configuration Strip Dropdowns */}

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            Season
          </label>
          <select
            className="bg-zinc-900 border border-zinc-700 text-zinc-100 text-sm rounded-md px-3 py-1.5 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all cursor-pointer"
            value={selectedSeason}
            onChange={(e) => setSeason(parseInt(e.target.value))}
          >
            {seasons.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div className="w-px h-6 bg-zinc-800 mx-2" />

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            Race
          </label>
          <select
            className="bg-zinc-900 border border-zinc-700 text-zinc-100 text-sm rounded-md px-3 py-1.5 min-w-[140px] focus:ring-1 focus:ring-blue-500 outline-none transition-all cursor-pointer"
            value={selectedRaceId || ""}
            onChange={(e) => setRace(e.target.value)}
          >
            <option value="" disabled>
              Select Session
            </option>
            {races.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg shadow-sm">
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
            Target A
          </label>
          <select
            className="bg-transparent text-zinc-100 font-mono text-sm w-[60px] outline-none cursor-pointer"
            value={selectedDriverA || ""}
            onChange={(e) => setDrivers(e.target.value, selectedDriverB || "")}
          >
            <option value="" disabled>
              ---
            </option>
            {drivers.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code}
              </option>
            ))}
          </select>
        </div>

        <span className="text-zinc-600 font-bold text-xs">VS</span>

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-red-400 uppercase tracking-wider">
            Target B
          </label>
          <select
            className="bg-transparent text-zinc-100 font-mono text-sm w-[60px] outline-none cursor-pointer"
            value={selectedDriverB || ""}
            onChange={(e) => setDrivers(selectedDriverA || "", e.target.value)}
          >
            <option value="" disabled>
              ---
            </option>
            {drivers.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
