"use client";

import { useMemo } from "react";
import ReactECharts from "echarts-for-react";

interface TelemetryData {
  distance: Float32Array;
  speed: Float32Array;
  throttle: Float32Array;
  brake: Float32Array;
  rpm: Float32Array;
  gear: Float32Array;
}

interface TelemetryChartProps {
  dataA: TelemetryData;
  dataB?: TelemetryData;
  driverCodeA: string;
  driverCodeB?: string;
  errorB?: string;
}

export function TelemetryChart({
  dataA,
  dataB,
  driverCodeA,
  driverCodeB,
}: TelemetryChartProps) {
  const options = useMemo(() => {
    // Convert TypedArrays to [x, y] pair arrays for ECharts line series
    const toPairs = (
      xArr: Float32Array,
      yArr: Float32Array,
    ): [number, number][] => {
      const result: [number, number][] = new Array(xArr.length);
      for (let i = 0; i < xArr.length; i++) {
        result[i] = [xArr[i], yArr[i]];
      }
      return result;
    };

    // Colors: Driver A = Blue, Driver B = Red/Orange
    const colorA = "#3b82f6";
    const colorB = "#f97316";

    const gridOptions = [
      { top: "5%", height: "28%", left: "5%", right: "3%" }, // Speed
      { top: "38%", height: "18%", left: "5%", right: "3%" }, // Throttle / Brake
      { top: "61%", height: "18%", left: "5%", right: "3%" }, // RPM
    ];

    const series = [
      // ── Driver A ──
      {
        name: `${driverCodeA} Speed`,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: toPairs(dataA.distance, dataA.speed),
        showSymbol: false,
        lineStyle: { color: colorA, width: 1.5 },
        sampling: "lttb",
        large: true,
      },
      {
        name: `${driverCodeA} Throttle`,
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: toPairs(dataA.distance, dataA.throttle),
        showSymbol: false,
        lineStyle: { color: "#22c55e", width: 1 },
        sampling: "lttb",
        large: true,
      },
      {
        name: `${driverCodeA} Brake`,
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: toPairs(dataA.distance, dataA.brake),
        showSymbol: false,
        lineStyle: { color: "#ef4444", width: 1 },
        sampling: "lttb",
        large: true,
      },
      {
        name: `${driverCodeA} RPM`,
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: toPairs(dataA.distance, dataA.rpm),
        showSymbol: false,
        lineStyle: { color: "#a855f7", width: 1 },
        sampling: "lttb",
        large: true,
      },
    ];

    // ── Driver B overlay ──
    if (dataB && driverCodeB) {
      series.push(
        {
          name: `${driverCodeB} Speed`,
          type: "line",
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: toPairs(dataB.distance, dataB.speed),
          showSymbol: false,
          lineStyle: { color: colorB, width: 1.5 },
          sampling: "lttb",
          large: true,
        },
        {
          name: `${driverCodeB} Throttle`,
          type: "line",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: toPairs(dataB.distance, dataB.throttle),
          showSymbol: false,
          lineStyle: { color: "#84cc16", width: 1 },
          sampling: "lttb",
          large: true,
        },
        {
          name: `${driverCodeB} Brake`,
          type: "line",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: toPairs(dataB.distance, dataB.brake),
          showSymbol: false,
          lineStyle: { color: "#fb923c", width: 1 },
          sampling: "lttb",
          large: true,
        },
        {
          name: `${driverCodeB} RPM`,
          type: "line",
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: toPairs(dataB.distance, dataB.rpm),
          showSymbol: false,
          lineStyle: { color: "#e879f9", width: 1 },
          sampling: "lttb",
          large: true,
        },
      );
    }

    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross", animation: false },
        backgroundColor: "#18181b",
        borderColor: "#27272a",
        textStyle: { color: "#fafafa", fontFamily: "monospace", fontSize: 11 },
        valueFormatter: (v: number) =>
          typeof v === "number" ? v.toFixed(1) : v,
      },
      legend: {
        top: 0,
        right: 0,
        textStyle: { color: "#a1a1aa", fontSize: 10 },
        itemWidth: 12,
        itemHeight: 8,
      },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1, 2], start: 0, end: 100 },
        {
          type: "slider",
          xAxisIndex: [0, 1, 2],
          start: 0,
          end: 100,
          bottom: 0,
          height: 20,
          textStyle: { color: "#a1a1aa" },
          borderColor: "#27272a",
          fillerColor: "rgba(59,130,246,0.15)",
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
          name: "Time (s)",
          nameTextStyle: { color: "#71717a", fontSize: 10 },
          min: "dataMin",
          max: "dataMax",
          axisLabel: { color: "#a1a1aa", fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          gridIndex: 0,
          type: "value",
          name: "Speed (km/h)",
          nameTextStyle: { color: "#71717a", fontSize: 10 },
          splitLine: { lineStyle: { color: "#27272a" } },
          axisLabel: { color: "#a1a1aa", fontSize: 10 },
        },
        {
          gridIndex: 1,
          type: "value",
          min: 0,
          max: 100,
          splitLine: { show: false },
          axisLabel: { color: "#a1a1aa", fontSize: 10 },
        },
        {
          gridIndex: 2,
          type: "value",
          name: "RPM",
          nameTextStyle: { color: "#71717a", fontSize: 10 },
          splitLine: { lineStyle: { color: "#27272a" } },
          axisLabel: { color: "#a1a1aa", fontSize: 10 },
        },
      ],
      series,
    };
  }, [dataA, dataB, driverCodeA, driverCodeB]);

  return (
    <div className="w-full h-full min-h-[600px] bg-zinc-950/50 rounded-xl border border-zinc-900 p-2 shadow-inner">
      <ReactECharts
        option={options}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}
