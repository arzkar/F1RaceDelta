import { create } from "zustand";

interface UiStore {
  // Global Selections
  selectedSeason: number;
  selectedRaceId: string | null;

  // Head to head specific
  selectedDriverA: string | null;
  selectedDriverB: string | null;

  // Actions
  setSeason: (season: number) => void;
  setRace: (raceId: string) => void;
  setDrivers: (driverA: string | null, driverB: string | null) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  selectedSeason: 2025, // Default payload
  selectedRaceId: null,
  selectedDriverA: null,
  selectedDriverB: null,

  setSeason: (season) =>
    set({
      selectedSeason: season,
      selectedRaceId: null,
      selectedDriverA: null,
      selectedDriverB: null,
    }),
  setRace: (raceId) =>
    set({
      selectedRaceId: raceId,
      selectedDriverA: null,
      selectedDriverB: null,
    }),
  setDrivers: (driverA, driverB) =>
    set({ selectedDriverA: driverA || null, selectedDriverB: driverB || null }),
}));
