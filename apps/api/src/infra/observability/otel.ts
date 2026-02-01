import { diag, DiagConsoleLogger, DiagLogLevel, trace } from '@opentelemetry/api';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { NodeSDK } from '@opentelemetry/sdk-node';
import type { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { SimpleSpanProcessor } from '@opentelemetry/sdk-trace-base';

import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';

export const SERVICE_NAME = 'api';

/**
 * Minimal JSON file exporter so CI can audit traces without running a collector.
 * Output schema: { service: string, spans: [...], generated_at_utc: string }
 */
class JsonFileSpanExporter {
  private readonly spans: any[] = [];

  constructor(private readonly filePath: string) {}

  export(spans: ReadableSpan[], resultCallback: (result: { code: number; error?: Error }) => void): void {
    try {
      for (const s of spans) {
        const parentSpanId = (s as any).parentSpanId ?? (s.spanContext() as any).parentSpanId;
        this.spans.push({
          traceId: s.spanContext().traceId,
          spanId: s.spanContext().spanId,
          parentSpanId,
          name: s.name,
          kind: s.kind,
          startTime: s.startTime,
          endTime: s.endTime,
          status: s.status,
          attributes: s.attributes,
          events: s.events,
        });
      }
      resultCallback({ code: 0 });
    } catch (e: any) {
      resultCallback({ code: 1, error: e instanceof Error ? e : new Error(String(e)) });
    }
  }

  shutdown(): Promise<void> {
    return Promise.resolve();
  }

  forceFlush(): Promise<void> {
    return this.flushToFile();
  }

  async flushToFile(): Promise<void> {
    const fs = await import('node:fs');
    const path = await import('node:path');
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });

    const payload = {
      generated_at_utc: new Date().toISOString(),
      service: SERVICE_NAME,
      spans: this.spans,
    };

    fs.writeFileSync(this.filePath, JSON.stringify(payload, null, 2) + '\n', { encoding: 'utf-8' });
  }
}

let sdk: NodeSDK | null = null;
let fileExporter: JsonFileSpanExporter | null = null;

export async function startOtel(): Promise<void> {
  if (sdk) return;

  const diagEnabled = (process.env.OTEL_DIAG_LOG_LEVEL ?? '').toLowerCase();
  if (diagEnabled === 'debug') {
    diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
  }

  const traceExportPath = process.env.PR2_TRACE_EXPORT_PATH;
  fileExporter = traceExportPath ? new JsonFileSpanExporter(traceExportPath) : null;

  const processors = [];
  if (fileExporter) {
    processors.push(new SimpleSpanProcessor(fileExporter as any));
  }

  // Optional OTLP exporter (kept for future collector-based pipelines)
  const otlpEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
  const otlp = otlpEndpoint ? new OTLPTraceExporter({ url: otlpEndpoint }) : null;
  if (otlp) {
    processors.push(new SimpleSpanProcessor(otlp));
  }

  sdk = new NodeSDK({
    serviceName: SERVICE_NAME,
    spanProcessors: processors.length > 0 ? (processors as any) : undefined,
    instrumentations: [
      getNodeAutoInstrumentations({
        // socket.io isn't auto-instrumented reliably; we add manual spans in ws.gateway.
      }),
    ],
  });

  await sdk.start();
}

export async function stopOtel(): Promise<void> {
  if (!sdk) return;
  try {
    // Flush first so file exporter writes out.
    if (fileExporter) {
      await fileExporter.flushToFile();
    }
    await sdk.shutdown();
  } finally {
    sdk = null;
    fileExporter = null;
  }
}

export function getTracer() {
  return trace.getTracer(SERVICE_NAME);
}
