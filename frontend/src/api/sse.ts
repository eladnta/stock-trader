import { useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export function useSSE<T>(path: string): T | null {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    const es = new EventSource(`${BASE}${path}`);
    es.onmessage = (e) => {
      try { setData(JSON.parse(e.data)); } catch {}
    };
    return () => es.close();
  }, [path]);

  return data;
}
