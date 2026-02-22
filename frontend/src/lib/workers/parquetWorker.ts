import * as parquet from "parquet-wasm";

export interface TelemetryData {
  Distance: Float32Array;
  Speed: Float32Array;
  Throttle: Float32Array;
  Brake: Float32Array;
  RPM: Float32Array;
  nGear: Float32Array;
}

self.onmessage = async (e: MessageEvent) => {
  const url = e.data.url as string;

  try {
    // 1. Fetch the raw binary ArrayBuffer from the Cloudflare R2 presigned URL
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch telemetry from R2: ${response.statusText}`,
      );
    }

    const arrayBuffer = await response.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);

    // 2. Initialize the WebAssembly module
    // We use the WASM Engine to rapidly decode the parquet structure without JS object overhead
    await parquet.default();

    // 3. Decode the Parquet file
    // Read the entire file into memory as an Arrow Table representation
    const table = parquet.readParquet(uint8Array);

    // This is a simplified extraction. `parquet-wasm` parses into Arrow IPC format natively.
    // We will extract the specific columns we need as Float32Arrays directly to avoid
    // converting 50,000 rows into JS generic Objects, strictly mapping to ECharts requirements.

    // To natively handle Arrow IPC in standard Next.js without massive payload overhead,
    // we parse the Arrow buffer directly.
    // For phase 6 demonstration, we will map the Arrow IPC to basic TypedArrays.
    // (Assuming apache-arrow is used under the hood or we pull the column batches directly).

    // *NOTE: The exact binary extraction depends heavily on the arrow IPC layout output by parquet-wasm.
    // We will send the raw IPC buffer back to the main thread for zero-copy EChart population
    // if `apache-arrow` library is installed on the main thread,
    // OR we map it to TypedArrays right here.

    // For elite performance, we send the raw IPC Uint8Array back to the main thread
    // where `apache-arrow` table.from() will instantly zero-copy map it.
    const ipcBuffer = table.intoIPCStream();

    // 4. Send back the highly optimized buffer.
    // We use Transferable Objects for zero-copy memory transfer between Worker and Main Thread.
    (self as unknown as Worker).postMessage(
      { success: true, ipcBuffer: ipcBuffer },
      [ipcBuffer.buffer],
    );
  } catch (error: any) {
    (self as unknown as Worker).postMessage({
      success: false,
      error: error.message,
    });
  }
};
