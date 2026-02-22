// hooks/useTelemetryWorker.ts
import { useEffect, useState, useRef } from "react";
import * as arrow from "apache-arrow";

export interface DecodedTelemetry {
  distance: Float32Array;
  speed: Float32Array;
  throttle: Float32Array;
  brake: Float32Array;
  rpm: Float32Array;
  gear: Float32Array;
}

/**
 * Filters the decoded Arrow table to a single representative lap.
 * Picks the lap with the longest time span (most complete clean lap).
 */
function extractBestLap(table: arrow.Table): DecodedTelemetry {
  const castFloat32 = (colName: string): Float32Array => {
    const col = table.getChild(colName);
    if (!col) return new Float32Array(0);
    const raw = col.toArray();
    // Arrow may return BigInt64Array for Int64 columns — Float32Array constructor
    // cannot accept BigInt types, so we must convert through plain numbers first.
    if (raw instanceof BigInt64Array || raw instanceof BigUint64Array) {
      return new Float32Array(Array.from(raw, (v) => Number(v)));
    }
    return new Float32Array(raw);
  };

  // lap_number is stored as Int in the Parquet schema — extract as plain numbers
  const lapCol = table.getChild("lap_number");
  const allLapNumbers: number[] = lapCol
    ? Array.from(lapCol.toArray(), (v) => Number(v))
    : [];

  const allTimestamp = castFloat32("timestamp");
  const allSpeed = castFloat32("speed");
  const allThrottle = castFloat32("throttle");
  const allBrake = castFloat32("brake");
  const allRpm = castFloat32("rpm");
  const allGear = castFloat32("gear");

  if (allLapNumbers.length === 0 || allTimestamp.length === 0) {
    return {
      distance: allTimestamp,
      speed: allSpeed,
      throttle: allThrottle,
      brake: allBrake,
      rpm: allRpm,
      gear: allGear,
    };
  }

  // Group contiguous row indices by lap_number
  const lapRanges: { lap: number; start: number; end: number }[] = [];
  let currentLap = allLapNumbers[0];
  let currentStart = 0;

  for (let i = 1; i <= allLapNumbers.length; i++) {
    if (i === allLapNumbers.length || allLapNumbers[i] !== currentLap) {
      lapRanges.push({ lap: currentLap, start: currentStart, end: i });
      if (i < allLapNumbers.length) {
        currentLap = allLapNumbers[i];
        currentStart = i;
      }
    }
  }

  // Find the lap with the longest time span (most complete clean lap)
  let bestRange = lapRanges[0];
  let bestDuration = -1;
  for (const range of lapRanges) {
    const count = range.end - range.start;
    // A clean lap at 10Hz should have > 500 samples (~50+ seconds)
    if (count > 200) {
      const duration = allTimestamp[range.end - 1] - allTimestamp[range.start];
      if (duration > bestDuration) {
        bestDuration = duration;
        bestRange = range;
      }
    }
  }

  // Fallback: if no lap qualifies, pick the one with the most data points
  if (bestDuration === -1) {
    let maxCount = 0;
    for (const range of lapRanges) {
      const count = range.end - range.start;
      if (count > maxCount) {
        maxCount = count;
        bestRange = range;
      }
    }
  }

  const { start, end } = bestRange;
  return {
    distance: allTimestamp.subarray(start, end),
    speed: allSpeed.subarray(start, end),
    throttle: allThrottle.subarray(start, end),
    brake: allBrake.subarray(start, end),
    rpm: allRpm.subarray(start, end),
    gear: allGear.subarray(start, end),
  };
}

export function useTelemetry(presignedUrl: string | null) {
  const [data, setData] = useState<DecodedTelemetry | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    if (!presignedUrl) return;

    setLoading(true);
    setError(null);

    // Initialize Next.js Web Worker natively
    workerRef.current = new Worker(
      new URL("../lib/workers/parquetWorker.ts", import.meta.url),
      {
        type: "module",
      },
    );

    workerRef.current.onmessage = (event: MessageEvent) => {
      const { success, ipcBuffer, error } = event.data;

      if (!success) {
        setError(error || "Worker crashed decoding Parquet traces.");
        setLoading(false);
        return;
      }

      try {
        const table = arrow.tableFromIPC(ipcBuffer);
        const singleLap = extractBestLap(table);
        setData(singleLap);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(`Arrow IPC mapping failed: ${err.message}`);
        } else {
          setError(`Arrow IPC mapping failed: Unknown error`);
        }
      } finally {
        setLoading(false);
      }
    };

    // Pass the absolute WASM URL from the main thread because workers spawned
    // via blob URLs in Next.js Turbopack cannot resolve relative paths.
    const wasmUrl = `${window.location.origin}/parquet_wasm_bg.wasm`;
    workerRef.current.postMessage({ url: presignedUrl, wasmUrl });

    return () => {
      workerRef.current?.terminate();
    };
  }, [presignedUrl]);

  return { data, loading, error };
}
