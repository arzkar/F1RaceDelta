"use client";

import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";

interface MonteCarloChartProps {
  driverACode: string;
  driverBCode: string;
  winPctA: number;
  winPctB: number;
}

export function MonteCarloChart({
  driverACode,
  driverBCode,
  winPctA,
  winPctB,
}: MonteCarloChartProps) {
  const options = useMemo(() => {
    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (
          params: echarts.DefaultLabelFormatterCallbackParams[] | any,
        ) => {
          const data = params[0];
          return `<div style="font-family: monospace; font-size: 14px;"><strong>${data.name}</strong><br/>Win Probability: ${(data.value as number).toFixed(1)}%</div>`;
        },
        backgroundColor: "#18181b",
        textStyle: { color: "#fafafa" },
        borderColor: "#27272a",
      },
      grid: {
        left: "10%",
        right: "10%",
        top: "20%",
        bottom: "20%",
      },
      xAxis: {
        type: "value",
        max: 100,
        splitLine: { show: false },
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { show: false },
      },
      yAxis: {
        type: "category",
        data: ["Win Probability"],
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { show: false },
      },
      series: [
        {
          name: driverACode,
          type: "bar",
          stack: "total",
          label: {
            show: true,
            formatter: `{a}: {c}%`,
            fontFamily: "monospace",
            fontSize: 14,
            color: "#fff",
          },
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: "#2563eb" },
              { offset: 1, color: "#3b82f6" },
            ]),
            borderRadius: [8, 0, 0, 8], // SaaS rounded edges
          },
          data: [winPctA],
        },
        {
          name: driverBCode,
          type: "bar",
          stack: "total",
          label: {
            show: true,
            formatter: `{a}: {c}%`,
            position: "insideLeft",
            fontFamily: "monospace",
            fontSize: 14,
            color: "#fff",
          },
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: "#f43f5e" },
              { offset: 1, color: "#e11d48" },
            ]),
            borderRadius: [0, 8, 8, 0],
          },
          data: [winPctB],
        },
      ],
      animationDuration: 1500,
      animationEasing: "cubicOut",
    };
  }, [driverACode, driverBCode, winPctA, winPctB]);

  return (
    <div className="w-full h-32 bg-zinc-950/50 rounded-xl border border-zinc-900 shadow-inner overflow-hidden">
      <ReactECharts
        option={options}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
}
