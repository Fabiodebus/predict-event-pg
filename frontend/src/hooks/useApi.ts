import { fetchAuthSession } from "aws-amplify/auth";
import { useCallback, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface UseApiResult<T> {
  call: (path: string, init?: RequestInit) => Promise<T>;
  loading: boolean;
  error: Error | null;
  data: T | null;
}

async function getAuthHeader(): Promise<Record<string, string>> {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    return idToken ? { Authorization: `Bearer ${idToken}` } : {};
  } catch {
    // No session — let backend 401 if the route requires auth.
    return {};
  }
}

export function useApi<T = unknown>(): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const call = useCallback(async (path: string, init: RequestInit = {}): Promise<T> => {
    setLoading(true);
    setError(null);
    try {
      const authHeader = await getAuthHeader();
      const response = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...authHeader,
          ...(init.headers ?? {}),
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const body = (await response.json()) as T;
      setData(body);
      return body;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { call, loading, error, data };
}
