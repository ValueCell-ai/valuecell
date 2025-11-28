export type SystemInfo = {
  access_token: string;
  refresh_token: string;
  id: string;
  email: string;
  name: string;
  avatar: string;
  created_at: string;
  updated_at: string;
};

export interface StrategyRankItem {
  id: number;
  name: string;
  avatar: string;
  return_rate_pct: number;
  strategy_type: string;
  llm_provider: string;
  llm_model_id: string;
  exchange_id: string;
}

export interface StrategyDetail {
  id: number;
  user_id: string;
  name: string;
  avatar: string;
  return_rate_pct: number;
  strategy_type: string;
  exchange: string;
  symbols: string[];
  max_leverage: number;
  initial_capital: number;
  prompt: string;
}
