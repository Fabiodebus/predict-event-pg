import { useEffect, useRef, useState } from "react";

import { useApi } from "./useApi";

export type JobStatus = "pending" | "in_progress" | "completed" | "failed";

export interface JobPollResponse {
  status: JobStatus;
  result: unknown;
  error: string | null;
}

export interface UsePollJobOptions {
  intervalMs?: number;
}

export interface UsePollJobResult {
  status: JobStatus | null;
  result: unknown;
  error: string | null;
  isPolling: boolean;
}

const DEFAULT_INTERVAL_MS = 2000;
const TERMINAL_STATES: ReadonlySet<JobStatus> = new Set(["completed", "failed"]);

export function usePollJob(
  jobId: string | null,
  options: UsePollJobOptions = {},
): UsePollJobResult {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const { call } = useApi<JobPollResponse>();

  const [status, setStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // call is recreated each render by useApi; pin a ref so the polling
  // closure doesn't restart the cycle on every parent re-render.
  const callRef = useRef(call);
  callRef.current = call;

  useEffect(() => {
    if (!jobId) {
      setIsPolling(false);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    setIsPolling(true);

    const tick = async () => {
      try {
        const job = await callRef.current(`/api/v1/agents/jobs/${jobId}`);
        if (cancelled) return;
        setStatus(job.status);
        setResult(job.result);
        setError(job.error);
        if (TERMINAL_STATES.has(job.status)) {
          setIsPolling(false);
          return;
        }
        timer = setTimeout(() => void tick(), intervalMs);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setIsPolling(false);
      }
    };

    void tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      setIsPolling(false);
    };
  }, [jobId, intervalMs]);

  return { status, result, error, isPolling };
}
