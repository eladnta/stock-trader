import useSWR from "swr";
import { fetchAPI } from "../api/client";
import { AnalysisResult } from "../types";

export function useAnalysis(ticker: string | null) {
  const { data, isLoading } = useSWR<AnalysisResult>(
    ticker ? `/analysis/${ticker}` : null,
    (path: string) => fetchAPI<AnalysisResult>(path),
    { refreshInterval: 60_000 }
  );
  return { analysis: data ?? null, loading: isLoading };
}
