"use client";

import { useUiStore } from "@/store/uiStore";
import { useEffect, useState } from "react";

interface RaceResponse {
  id: string;
  grand_prix: string;
}

interface DriverResponse {
  driver_code: string;
  full_name: string;
}

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

  const [seasons, setSeasons] = useState<number[]>([]);
  const [races, setRaces] = useState<{ id: string; name: string }[]>([]);
  const [drivers, setDriversList] = useState<{ code: string; name: string }[]>(
    [],
  );

  // 1. Load Seasons on mount
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/seasons`)
      .then((res) => res.json())
      .then((data) => setSeasons(data))
      .catch((err) => console.error("Failed to fetch seasons", err));
  }, []);

  // 2. Load Races when Season changes
  useEffect(() => {
    if (!selectedSeason) return;
    fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/seasons/${selectedSeason}/races`,
    )
      .then((res) => res.json())
      .then((data) => {
        setRaces(
          data.map((r: RaceResponse) => ({ id: r.id, name: r.grand_prix })),
        );
      })
      .catch((err) => console.error("Failed to fetch races", err));
  }, [selectedSeason]);

  // 3. Load Drivers when Race changes
  useEffect(() => {
    if (!selectedRaceId) return;
    fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/races/${selectedRaceId}/drivers`,
    )
      .then((res) => res.json())
      .then((data) => {
        setDriversList(
          data.map((d: DriverResponse) => ({
            code: d.driver_code,
            name: d.full_name,
          })),
        );
      })
      .catch((err) => console.error("Failed to fetch drivers", err));
  }, [selectedRaceId]);

  const selectClass =
    "bg-[var(--panel)] border border-[var(--border)] text-[var(--fg)] text-sm rounded-md px-3 py-1.5 focus:ring-1 focus:ring-blue-500 outline-none transition-all cursor-pointer";
  const driverSelectClass =
    "bg-transparent text-[var(--fg)] font-mono text-sm w-[70px] outline-none cursor-pointer";

  return (
    <header className="h-16 flex-shrink-0 bg-[var(--surface)]/80 backdrop-blur-md border-b border-[var(--border)] flex items-center justify-between px-6 sticky top-0 z-50">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
            Season
          </label>
          <select
            className={selectClass}
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

        <div className="w-px h-6 bg-[var(--border)] mx-2" />

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
            Race
          </label>
          <select
            className={`${selectClass} min-w-[140px]`}
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

      <div className="flex items-center gap-4 bg-[var(--panel)] border border-[var(--border)] px-3 py-1.5 rounded-lg shadow-sm">
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
            Driver A
          </label>
          <select
            className={driverSelectClass}
            value={selectedDriverA || ""}
            onChange={(e) =>
              setDrivers(e.target.value || null, selectedDriverB)
            }
          >
            <option value="">None</option>
            {drivers.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code}
              </option>
            ))}
          </select>
        </div>

        <span className="text-[var(--muted)] font-bold text-xs">VS</span>

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-red-400 uppercase tracking-wider">
            Driver B
          </label>
          <select
            className={driverSelectClass}
            value={selectedDriverB || ""}
            onChange={(e) =>
              setDrivers(selectedDriverA, e.target.value || null)
            }
          >
            <option value="">None</option>
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
