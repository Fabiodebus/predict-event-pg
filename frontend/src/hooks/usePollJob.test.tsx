import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const callMock = vi.fn();

vi.mock("./useApi", () => ({
  useApi: () => ({
    call: callMock,
    loading: false,
    error: null,
    data: null,
  }),
}));

import { usePollJob } from "./usePollJob";

beforeEach(() => {
  callMock.mockReset();
  // shouldAdvanceTime keeps real time moving so testing-library's waitFor
  // can retry; vi.advanceTimersByTimeAsync still drives the polling cycle.
  vi.useFakeTimers({ shouldAdvanceTime: true, advanceTimeDelta: 20 });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("usePollJob", () => {
  it("polls until status is completed and stops", async () => {
    callMock
      .mockResolvedValueOnce({ status: "in_progress", result: null, error: null })
      .mockResolvedValueOnce({ status: "in_progress", result: null, error: null })
      .mockResolvedValueOnce({
        status: "completed",
        result: { ok: true },
        error: null,
      });

    const { result } = renderHook(() => usePollJob("job-1", { intervalMs: 100 }));

    await waitFor(() => expect(callMock).toHaveBeenCalledTimes(1));
    await vi.advanceTimersByTimeAsync(100);
    await waitFor(() => expect(callMock).toHaveBeenCalledTimes(2));
    await vi.advanceTimersByTimeAsync(100);
    await waitFor(() => expect(callMock).toHaveBeenCalledTimes(3));

    await waitFor(() => expect(result.current.status).toBe("completed"));
    expect(result.current.result).toEqual({ ok: true });
    expect(result.current.isPolling).toBe(false);

    // Confirm no further polls fire after terminal state.
    await vi.advanceTimersByTimeAsync(500);
    expect(callMock).toHaveBeenCalledTimes(3);
  });

  it("stops polling on failed status", async () => {
    callMock.mockResolvedValueOnce({
      status: "failed",
      result: null,
      error: "boom",
    });

    const { result } = renderHook(() => usePollJob("job-2", { intervalMs: 50 }));

    await waitFor(() => expect(result.current.status).toBe("failed"));
    expect(result.current.error).toBe("boom");
    expect(result.current.isPolling).toBe(false);
  });

  it("does not poll when jobId is null", () => {
    renderHook(() => usePollJob(null, { intervalMs: 50 }));
    expect(callMock).not.toHaveBeenCalled();
  });

  it("surfaces fetch error and stops polling", async () => {
    callMock.mockRejectedValueOnce(new Error("network down"));

    const { result } = renderHook(() => usePollJob("job-3", { intervalMs: 50 }));

    await waitFor(() => expect(result.current.error).toBe("network down"));
    expect(result.current.isPolling).toBe(false);
  });

  it("stops polling on unmount before terminal state", async () => {
    callMock.mockResolvedValue({
      status: "in_progress",
      result: null,
      error: null,
    });

    const { unmount } = renderHook(() =>
      usePollJob("job-4", { intervalMs: 100 }),
    );

    await waitFor(() => expect(callMock).toHaveBeenCalledTimes(1));
    unmount();
    await vi.advanceTimersByTimeAsync(500);
    expect(callMock).toHaveBeenCalledTimes(1);
  });
});
