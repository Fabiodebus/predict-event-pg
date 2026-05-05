import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn(),
}));

import { fetchAuthSession } from "aws-amplify/auth";

import { useApi } from "./useApi";

const mockFetchAuthSession = vi.mocked(fetchAuthSession);

const originalFetch = globalThis.fetch;
const fetchSpy = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchSpy);
  fetchSpy.mockReset();
  mockFetchAuthSession.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  globalThis.fetch = originalFetch;
});

function mockSession(idToken: string | undefined) {
  mockFetchAuthSession.mockResolvedValue({
    tokens: idToken
      ? { idToken: { toString: () => idToken } }
      : undefined,
  } as never);
}

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("useApi", () => {
  it("injects Authorization: Bearer from Cognito id token", async () => {
    mockSession("ID-TOKEN-123");
    fetchSpy.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const { result } = renderHook(() => useApi<{ ok: boolean }>());
    await act(async () => {
      await result.current.call("/api/v1/health");
    });

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [, init] = fetchSpy.mock.calls[0]!;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer ID-TOKEN-123");
  });

  it("returns parsed JSON in data on 2xx", async () => {
    mockSession("tok");
    fetchSpy.mockResolvedValueOnce(jsonResponse({ value: 42 }));

    const { result } = renderHook(() => useApi<{ value: number }>());
    await act(async () => {
      await result.current.call("/api/v1/anything");
    });

    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
  });

  it("toggles loading around the call", async () => {
    mockSession("tok");
    let resolve!: (r: Response) => void;
    fetchSpy.mockReturnValueOnce(
      new Promise<Response>((r) => {
        resolve = r;
      }),
    );

    const { result } = renderHook(() => useApi());
    let pending: Promise<unknown>;
    act(() => {
      pending = result.current.call("/api/v1/anything");
    });

    await waitFor(() => expect(result.current.loading).toBe(true));

    await act(async () => {
      resolve(jsonResponse({}));
      await pending;
    });

    expect(result.current.loading).toBe(false);
  });

  it("surfaces non-2xx response as error", async () => {
    mockSession("tok");
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ error_code: "FORBIDDEN" }), {
        status: 403,
        statusText: "Forbidden",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useApi());
    await act(async () => {
      await expect(result.current.call("/api/v1/anything")).rejects.toThrow(
        /403/,
      );
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toMatch(/403/);
  });

  it("surfaces network rejection as error", async () => {
    mockSession("tok");
    fetchSpy.mockRejectedValueOnce(new TypeError("network failure"));

    const { result } = renderHook(() => useApi());
    await act(async () => {
      await expect(result.current.call("/api/v1/anything")).rejects.toThrow(
        /network/,
      );
    });
    expect(result.current.error?.message).toMatch(/network/);
  });

  it("makes request without Authorization when no session", async () => {
    mockFetchAuthSession.mockRejectedValueOnce(
      new Error("UserUnAuthenticated"),
    );
    fetchSpy.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const { result } = renderHook(() => useApi());
    await act(async () => {
      await result.current.call("/api/v1/health");
    });

    const [, init] = fetchSpy.mock.calls[0]!;
    const headers = (init.headers ?? {}) as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });
});
