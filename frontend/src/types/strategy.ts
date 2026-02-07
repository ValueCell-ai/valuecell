// Strategy types

export interface Strategy {
  strategy_id: number;
  strategy_name: string;
  strategy_type: "PromptBasedStrategy" | "GridStrategy";
  status: "running" | "stopped";
  stop_reason?: string;
  trading_mode: "live" | "virtual";
  total_pnl: number;
  total_pnl_pct: number;
  created_at: string;
  exchange_id: string;
  model_id: string;
  stop_reason?: string; // Stop reason (e.g., "stop_loss", "cancelled", etc.)
}

// Strategy Performance types
export type StrategyPerformance = {
  strategy_id: string;
  initial_capital: number;
  return_rate_pct: number;
  llm_provider: string;
  llm_model_id: string;
  exchange_id: string;
  strategy_type: Strategy["strategy_type"];
  max_leverage: number;
  symbols: string[];
  prompt: string;
  prompt_name: string;
  trading_mode: Strategy["trading_mode"];
  decide_interval: number;
};

// Position types
export interface Position {
  symbol: string;
  type: "LONG" | "SHORT";
  leverage: number;
  entry_price: number;
  quantity: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

// Strategy Action types
export interface StrategyAction {
  instruction_id: string;
  symbol: string;
  action: "open_long" | "open_short" | "close_long" | "close_short";
  action_display: string;
  side: "BUY" | "SELL";
  quantity: number;
  leverage: number;
  entry_price: number;
  exit_price?: number;
  entry_at: string;
  exit_at?: string;
  fee_cost: number;
  realized_pnl: number;
  realized_pnl_pct: number;
  rationale: string;
  holding_time_ms: number;
}

// Strategy Compose types
export interface StrategyCompose {
  compose_id: string;
  created_at: string;
  rationale: string;
  cycle_index: number;
  actions: StrategyAction[];
}

// Strategy Prompt types
export interface StrategyPrompt {
  id: string;
  name: string;
  content: string;
}

// Create Strategy types
export interface CreateStrategy {
  // LLM Model Configuration
  llm_model_config: {
    provider: string; // e.g. 'openrouter'
    model_id: string; // e.g. 'deepseek-ai/deepseek-v3.1'
    api_key: string;
  };

  // Exchange Configuration
  exchange_config: {
    exchange_id: string; // e.g. 'okx'
    trading_mode: "live" | "virtual";
    api_key: string;
    secret_key: string;
    passphrase: string; // Required for some exchanges like OKX
    wallet_address: string;
    private_key: string;
  };

  // Trading Strategy Configuration
  trading_config: {
    strategy_name: string;
    initial_capital: number;
    max_leverage: number;
    symbols: string[]; // e.g. ['BTC', 'ETH', ...]
    template_id: string;
    custom_prompt?: string;
    decide_interval: number;
    strategy_type: Strategy["strategy_type"];
  };
}

// Copy Strategy types
export interface CopyStrategy {
  // LLM Model Configuration
  llm_model_config: {
    provider: string; // e.g. 'openrouter'
    model_id: string; // e.g. 'deepseek-ai/deepseek-v3.1'
    api_key: string;
  };

  // Exchange Configuration
  exchange_config: {
    exchange_id: string; // e.g. 'okx'
    trading_mode: "live" | "virtual";
    api_key: string;
    secret_key: string;
    passphrase: string; // Required for some exchanges like OKX
    wallet_address: string;
    private_key: string;
  };

  // Trading Strategy Configuration
  trading_config: {
    strategy_name: string;
    initial_capital: number;
    max_leverage: number;
    symbols: string[]; // e.g. ['BTC', 'ETH', ...]
    decide_interval: number;
    strategy_type: Strategy["strategy_type"];
    prompt_name: string;
    prompt: string;
    decide_interval?: number; // Decision interval in seconds (default: 60)
    dynamicConfig?: DynamicStrategyConfig; // 动态策略配置（可选）
  };
}

// Portfolio Summary types
export interface PortfolioSummary {
  cash: number;
  total_value: number;
  total_pnl: number;
}

// Dynamic Strategy Configuration types
export type BaseStrategyType = "TREND" | "GRID" | "BREAKOUT" | "ARBITRAGE";
export type SwitchMode = "SCORE" | "MANUAL";
export type RiskMode = "AGGRESSIVE" | "NEUTRAL" | "DEFENSIVE";

export interface ScoreWeights {
  volatility: number; // 波动率权重 (0-1)
  trendStrength: number; // 趋势强度权重 (0-1)
  volumeRatio: number; // 成交量比率权重 (0-1)
  marketSentiment: number; // 市场情绪权重 (0-1)
}

export interface DynamicStrategyConfig {
  baseStrategy: BaseStrategyType[]; // 基础策略池
  switchMode: SwitchMode; // 切换模式：评分自动切换 或 手动指定
  scoreWeights: ScoreWeights; // 各指标的权重 (总和应为1)
  riskMode: RiskMode; // 整体风险偏好
}

// Market State and Strategy Scores
export interface StrategyScore {
  name: string;
  score: number; // 0-100
  reason?: string; // 得分原因说明
}

export interface MarketStateAndScores {
  currentState: string; // 当前市场状态描述
  strategyScores: StrategyScore[]; // 各策略得分
  recommendedStrategy: string; // 推荐策略
  marketIndicators: {
    volatility: number;
    trendStrength: number;
    volumeRatio: number;
    marketSentiment: number;
  };
}

// Backtest Configuration
export interface BacktestConfig {
  strategyId?: string; // 策略ID（用于回测已有策略）
  strategyConfig?: CreateStrategyRequest; // 策略配置（用于回测新策略）
  startDate: string; // 回测开始日期 (ISO format)
  endDate: string; // 回测结束日期 (ISO format)
  initialCapital: number; // 初始资金
}

export interface BacktestResult {
  backtestId: string;
  totalReturn: number; // 总收益率
  totalReturnPct: number; // 总收益率百分比
  sharpeRatio: number; // 夏普比率
  maxDrawdown: number; // 最大回撤
  maxDrawdownPct: number; // 最大回撤百分比
  winRate: number; // 胜率
  totalTrades: number; // 总交易次数
  startDate: string;
  endDate: string;
  equityCurve: Array<[number, number]>; // [timestamp, equity] 权益曲线
  trades: Array<{
    symbol: string;
    action: string;
    entryPrice: number;
    exitPrice: number;
    quantity: number;
    pnl: number;
    pnlPct: number;
    entryTime: string;
    exitTime: string;
  }>;
}

// Position Control Update
export interface PositionControlUpdate {
  strategyId: string;
  maxPositions?: number; // 最大持仓数量
  maxPositionQty?: number; // 单个标的最大持仓量
  maxLeverage?: number; // 最大杠杆
  positionSize?: Record<string, number>; // 各标的的仓位大小 (symbol -> quantity)
}

// Manual Close Position
export interface ManualClosePositionRequest {
  strategyId: string;
  symbol: string;
  closeRatio: number; // 0.0 - 1.0
}

export interface ManualClosePositionData {
  strategyId: string;
  symbol: string;
  closedQuantity: number;
  closeRatio: number;
  message: string;
}

