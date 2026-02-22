"use client";

import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";

interface TelemetryChartProps {
  data: {
    distance: Float32Array;
    speed: Float32Array;
    throttle: Float32Array;
    brake: Float32Array;
    rpm: Float32Array;
    gear: Float32Array;
  };
  driverCode: string;
  compoundColor: string;
}

export function TelemetryChart({
  data,
  driverCode,
  compoundColor,
}: TelemetryChartProps) {
  // We memoize the ECharts options precisely so React re-renders don't destroy WebGL memory
  const options = useMemo(() => {
    // ECharts 5 natively supports column-based TypedArrays inside the Dataset object
    // This completely bypasses the catastrophic performance loss of Array.from() or deep JS Maps
    const dataset = {
      dimensions: ["Distance", "Speed", "Throttle", "Brake", "RPM", "Gear"],
      source: {
        Distance: data.distance,
        Speed: data.speed,
        Throttle: data.throttle,
        Brake: data.brake,
        RPM: data.rpm,
        Gear: data.gear,
      },
    };

    const gridOptions = [
      { top: "5%", height: "30%", left: "5%", right: "3%" }, // Speed
      { top: "40%", height: "20%", left: "5%", right: "3%" }, // Throttle / Brake
      { top: "65%", height: "25%", left: "5%", right: "3%" }, // RPM / Gear
    ];

    return {
      dataset,
      // Grouping ensures synchronized tooltips across the vertical stack
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross", animation: false },
        backgroundColor: "#18181b",
        borderColor: "#27272a",
        textStyle: { color: "#fafafa", fontFamily: "monospace" },
      },
      axisPointer: { link: { xAxisIndex: "all" } }, // Synced crosshairs!
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1, 2], start: 0, end: 100 },
        {
          type: "slider",
          xAxisIndex: [0, 1, 2],
          start: 0,
          end: 100,
          bottom: 0,
          textStyle: { color: "#a1a1aa" },
        },
      ],
      grid: gridOptions,
      xAxis: [
        {
          type: "value",
          gridIndex: 0,
          show: false,
          min: "dataMin",
          max: "dataMax",
        },
        {
          type: "value",
          gridIndex: 1,
          show: false,
          min: "dataMin",
          max: "dataMax",
        },
        {
          type: "value",
          gridIndex: 2,
          min: "dataMin",
          max: "dataMax",
          axisLabel: { color: "#a1a1aa" },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          gridIndex: 0,
          type: "value",
          name: "Speed (km/h)",
          nameTextStyle: { color: "#a1a1aa" },
          splitLine: { lineStyle: { color: "#27272a" } },
          axisLabel: { color: "#a1a1aa" },
        },
        {
          gridIndex: 1,
          type: "value",
          min: 0,
          max: 100,
          splitLine: { show: false },
          axisLabel: { color: "#a1a1aa" },
        },
        {
          gridIndex: 2,
          type: "value",
          name: "RPM",
          nameTextStyle: { color: "#a1a1aa" },
          splitLine: { lineStyle: { color: "#27272a" } },
          axisLabel: { color: "#a1a1aa" },
        },
      ],
      series: [
        // Top Grid: Speed
        {
          name: `${driverCode} Speed`,
          type: "line",
          xAxisIndex: 0,
          yAxisIndex: 0,
          encode: { x: "Distance", y: "Speed" },
          showSymbol: false,
          lineStyle: { color: compoundColor, width: 2 },
          // Extreme performance flag skipping JS sampling
          sampling: "lttb",
        },
        // Mid Grid: Throttle
        {
          name: `${driverCode} Throttle`,
          type: "line",
          xAxisIndex: 1,
          yAxisIndex: 1,
          encode: { x: "Distance", y: "Throttle" },
          showSymbol: false,
          lineStyle: { color: "#22c55e", width: 1.5 }, // Green
          sampling: "lttb",
        },
        // Mid Grid: Brake
        {
          name: `${driverCode} Brake`,
          type: "line",
          xAxisIndex: 1,
          yAxisIndex: 1,
          encode: { x: "Distance", y: "Brake" },
          showSymbol: false,
          lineStyle: { color: "#ef4444", width: 1.5 }, // Red
          sampling: "lttb",
        },
        // Bottom Grid: RPM
        {
          name: `${driverCode} RPM`,
          type: "line",
          xAxisIndex: 2,
          yAxisIndex: 2,
          encode: { x: "Distance", y: "RPM" },
          showSymbol: false,
          lineStyle: { color: "#a855f7", width: 1.5 }, // Purple
          sampling: "lttb",
        },
      ],
    };
  }, [data, driverCode, compoundColor]);

  return (
    <div className="w-full h-full min-h-[600px] bg-zinc-950/50 rounded-xl border border-zinc-900 p-2 shadow-inner">
      <ReactECharts
        option={options}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }} // Enforce WebGL/Canvas over SVG for 50k points
        notMerge={false}
        lazyUpdate={true}
      />
    </div>
  );
}
