"use client";

import React from "react";
import ReactEChartsCore from "echarts-for-react";

interface StrategyLap {
  lap_number: number;
  simulated_time_s: number;
  tyre_wear: number;
  fuel_mass_kg: number;
  compound: string;
}

interface StrategyChartProps {
  laps: StrategyLap[];
  pitLaps: number[];
  raceTotalLaps: number;
}

const COMPOUND_COLORS: Record<string, string> = {
  SOFT: "#ef4444",
  MEDIUM: "#eab308",
  HARD: "#d4d4d8",
  INTERMEDIATE: "#22c55e",
  WET: "#3b82f6",
};

export function StrategyChart({
  laps,
  pitLaps,
  raceTotalLaps,
}: StrategyChartProps) {
  if (!laps.length) return null;

  // Group laps into contiguous stint segments for individual series
  const stints: { compound: string; data: [number, number][] }[] = [];
  let current: { compound: string; data: [number, number][] } | null = null;

  for (const lap of laps) {
    if (!current || current.compound !== lap.compound) {
      // Overlap: add last point of previous stint as first of next for continuity
      current = { compound: lap.compound, data: [] };
      stints.push(current);
    }
    current.data.push([lap.lap_number, lap.simulated_time_s]);
  }

  // Build wear and fuel data across all laps
  const wearData = laps.map((l) => [l.lap_number, l.tyre_wear]);
  const fuelData = laps.map((l) => [l.lap_number, l.fuel_mass_kg]);

  const option: Record<string, unknown> = {
    animation: true,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "#18181b",
      borderColor: "#27272a",
      textStyle: { color: "#fafafa", fontFamily: "monospace", fontSize: 11 },
      valueFormatter: (v: number) => (typeof v === "number" ? v.toFixed(2) : v),
    },
    legend: {
      top: 0,
      right: 0,
      textStyle: { color: "#a1a1aa", fontSize: 10 },
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: [
      { left: 60, right: 60, top: 40, height: "45%" },
      { left: 60, right: 60, top: "62%", height: "30%" },
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 }],
    xAxis: [
      {
        gridIndex: 0,
        type: "value",
        name: "Lap",
        nameTextStyle: { color: "#71717a", fontSize: 10 },
        axisLabel: { color: "#a1a1aa", fontSize: 10 },
        axisLine: { lineStyle: { color: "#27272a" } },
        splitLine: { lineStyle: { color: "#27272a", opacity: 0.3 } },
        min: 1,
        max: Math.max(raceTotalLaps, laps.length),
      },
      {
        gridIndex: 1,
        type: "value",
        name: "Lap",
        nameTextStyle: { color: "#71717a", fontSize: 10 },
        axisLabel: { color: "#a1a1aa", fontSize: 10 },
        axisLine: { lineStyle: { color: "#27272a" } },
        splitLine: { lineStyle: { color: "#27272a", opacity: 0.3 } },
        min: 1,
        max: Math.max(raceTotalLaps, laps.length),
      },
    ],
    yAxis: [
      {
        gridIndex: 0,
        type: "value",
        name: "Lap Time (s)",
        nameTextStyle: { color: "#71717a", fontSize: 10 },
        axisLabel: { color: "#a1a1aa", fontSize: 10, formatter: "{value}s" },
        axisLine: { lineStyle: { color: "#27272a" } },
        splitLine: { lineStyle: { color: "#27272a", opacity: 0.3 } },
      },
      {
        gridIndex: 1,
        type: "value",
        name: "Tyre Wear",
        nameTextStyle: { color: "#71717a", fontSize: 10 },
        axisLabel: { color: "#a1a1aa", fontSize: 10 },
        axisLine: { lineStyle: { color: "#27272a" } },
        splitLine: { lineStyle: { color: "#27272a", opacity: 0.3 } },
      },
      {
        gridIndex: 1,
        type: "value",
        name: "Fuel (kg)",
        nameTextStyle: { color: "#71717a", fontSize: 10 },
        axisLabel: { color: "#60a5fa", fontSize: 10 },
        axisLine: { lineStyle: { color: "#60a5fa" } },
        splitLine: { show: false },
      },
    ],
    series: [
      // Lap time series per stint (compound-colored)
      ...stints.map((stint, i) => ({
        name: `Stint ${i + 1} (${stint.compound})`,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: stint.data,
        symbol: "none",
        lineStyle: {
          width: 2.5,
          color: COMPOUND_COLORS[stint.compound] || "#a1a1aa",
        },
        itemStyle: {
          color: COMPOUND_COLORS[stint.compound] || "#a1a1aa",
        },
      })),
      // Tyre wear
      {
        name: "Tyre Wear",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: wearData,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#f97316" },
        itemStyle: { color: "#f97316" },
      },
      // Fuel mass
      {
        name: "Fuel (kg)",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: fuelData,
        symbol: "none",
        lineStyle: { width: 1.5, color: "#60a5fa", type: "dashed" },
        itemStyle: { color: "#60a5fa" },
      },
      // Pit stop markers
      ...pitLaps.map((lap) => ({
        type: "line",
        markLine: {
          silent: true,
          symbol: "none",
          data: [{ xAxis: lap }],
          lineStyle: { color: "#a1a1aa", type: "dashed", width: 1 },
          label: { formatter: "PIT", color: "#a1a1aa", fontSize: 9 },
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: [],
      })),
    ],
  };

  return (
    <ReactEChartsCore
      option={option}
      style={{ height: "100%", width: "100%" }}
      notMerge
      lazyUpdate
    />
  );
}
