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
        // Instantly zero-copy map the IPC array buffer back into an Apache Arrow Table
        // avoiding all JS Object allocation crashes on massive 50K row sets
        const table = arrow.tableFromIPC(ipcBuffer);

        // For Apache ECharts efficiency, we extract the entire column native chunks directly
        // to Float32Arrays preventing standard `table.toArray()` JS object mapping crashes
        const castFloat32 = (colName: string): Float32Array => {
          const col = table.getChild(colName);
          if (!col) return new Float32Array(0);
          // In modern Apache Arrow, toArray() on a primitive vector natively returns the underlying TypedArray
          return col.toArray() as Float32Array;
        };
        const ext: DecodedTelemetry = {
          distance: castFloat32("Distance"),
          speed: castFloat32("Speed"),
          throttle: castFloat32("Throttle"),
          brake: castFloat32("Brake"),
          rpm: castFloat32("RPM"),
          gear: castFloat32("nGear"),
        };

        setData(ext);
      } catch (err: any) {
        setError(`Arrow IPC mapping failed: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    // Trigger the R2 fetch & WASM decode precisely when the presignedUrl changes
    workerRef.current.postMessage({ url: presignedUrl });

    return () => {
      workerRef.current?.terminate();
    };
  }, [presignedUrl]);

  return { data, loading, error };
}
