"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "./api";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

// Fetch a backend path on mount; `refreshKey` re-fetches when it changes.
export function useApi<T = any>(path: string, refreshKey: number = 0): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    let active = true;
    setLoading(true);
    setError(null);
    apiGet<T>(path)
      .then((d) => {
        if (active) {
          setData(d);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (active) {
          setError(e.message || "Failed to load");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [path]);

  useEffect(() => {
    const cleanup = load();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, refreshKey]);

  return { data, loading, error, reload: load };
}
