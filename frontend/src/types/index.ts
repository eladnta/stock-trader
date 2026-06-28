export interface Position {
  ticker: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  pnl_pct: number;
  action: "BUY" | "SELL" | "HOLD";
}

export interface ConvictionAccuracy {
  overall: number;
  by_horizon: Record<string, number>;  // "1W" | "1M" | "3M" -> accuracy %
}

export interface Portfolio {
  portfolio_value: number;
  total_return_pct: number;
  cash_pct: number;
  vs_spy_alpha: number | null;
  vs_qqq_alpha: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  positions: Record<string, Position>;
  conviction_accuracy: ConvictionAccuracy;
  as_of: string;
}

export interface SignalContribution {
  name: string;
  score: number;    // -1 to +1
  weight: number;
  label: string;
}

export interface AnalysisResult {
  ticker: string;
  action: string;
  opportunity_score: number;
  asset_class: string;
  sector?: string;
  price?: number;
  price_target?: number;
  signals?: SignalContribution[];
  thesis?: string;
}

export interface Signal {
  key: string;
  value: string;
  cached_at: string;
  type: string;
}
