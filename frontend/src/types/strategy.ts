// Strategy types

export interface Strategy {
  strategy_id: string;
  strategy_name: string;
  status: "running" | "stopped";
  trading_mode: "live" | "virtual";
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  created_at: string;
  exchange_id: string;
  model_id: string;
}

// Create Strategy Request types
export interface CreateStrategyRequest {
  // LLM Model Configuration
  LLMModelConfig: {
    provider: string; // e.g. 'openrouter'
    model_id: string; // e.g. 'deepseek-ai/deepseek-v3.1'
    api_key: string;
  };

  // Exchange Configuration
  exchangeConfig: {
    exchange_id: string; // e.g. 'okx'
    trading_mode: "live" | "virtual";
    api_key?: string;
    secret_key?: string;
  };

  // Trading Strategy Configuration
  tradingConfig: {
    strategy_name: string;
    initial_capital: number;
    max_leverage: number;
    symbols: string[]; // e.g. ['BTC', 'ETH', ...]
    template_id: string;
    custom_prompt?: string;
  };
}
