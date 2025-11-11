import {
  AswathDamodaranPng,
  BenGrahamPng,
  BillAckmanPng,
  CathieWoodPng,
  CharlieMungerPng,
  EmotionalAgencyPng,
  FundamentalProxyPng,
  MichaelBurryPng,
  MohnishPabraiPng,
  NewPushAgentPng,
  PeterLynchPng,
  PhilFisherPng,
  PortfolioManagerPng,
  RakeshJhunjhunwalaPng,
  ResearchAgentPng,
  SecAgentPng,
  StanleyDruckenmillerPng,
  StrategyAgentPng,
  TechnicalAgencyPng,
  ValuationAgencyPng,
  ValueCellAgentPng,
  WarrenBuffettPng,
} from "@/assets/png";
import {
  ChatConversationRenderer,
  MarkdownRenderer,
  ReportRenderer,
  ScheduledTaskControllerRenderer,
  ScheduledTaskRenderer,
  ToolCallRenderer,
} from "@/components/valuecell/renderer";
import { TimeUtils } from "@/lib/time";
import type { AgentComponentType, AgentInfo } from "@/types/agent";
import type { RendererComponent } from "@/types/renderer";

// component_type to section type
export const AGENT_SECTION_COMPONENT_TYPE = ["scheduled_task_result"] as const;

// multi section component type
export const AGENT_MULTI_SECTION_COMPONENT_TYPE = ["report"] as const;

// agent component type
export const AGENT_COMPONENT_TYPE = [
  "markdown",
  "tool_call",
  "subagent_conversation",
  "scheduled_task_controller",
  ...AGENT_SECTION_COMPONENT_TYPE,
  ...AGENT_MULTI_SECTION_COMPONENT_TYPE,
] as const;

/**
 * Component renderer mapping with automatic type inference
 */
export const COMPONENT_RENDERER_MAP: {
  [K in AgentComponentType]: RendererComponent<K>;
} = {
  scheduled_task_result: ScheduledTaskRenderer,
  scheduled_task_controller: ScheduledTaskControllerRenderer,
  report: ReportRenderer,
  markdown: MarkdownRenderer,
  tool_call: ToolCallRenderer,
  subagent_conversation: ChatConversationRenderer,
};

export const AGENT_AVATAR_MAP: Record<string, string> = {
  // Investment Masters
  ResearchAgent: ResearchAgentPng,
  StrategyAgent: StrategyAgentPng,
  AswathDamodaranAgent: AswathDamodaranPng,
  BenGrahamAgent: BenGrahamPng,
  BillAckmanAgent: BillAckmanPng,
  CathieWoodAgent: CathieWoodPng,
  CharlieMungerAgent: CharlieMungerPng,
  MichaelBurryAgent: MichaelBurryPng,
  MohnishPabraiAgent: MohnishPabraiPng,
  PeterLynchAgent: PeterLynchPng,
  PhilFisherAgent: PhilFisherPng,
  RakeshJhunjhunwalaAgent: RakeshJhunjhunwalaPng,
  StanleyDruckenmillerAgent: StanleyDruckenmillerPng,
  WarrenBuffettAgent: WarrenBuffettPng,
  ValueCellAgent: ValueCellAgentPng,

  // Analyst Agents
  FundamentalsAnalystAgent: FundamentalProxyPng,
  TechnicalAnalystAgent: TechnicalAgencyPng,
  ValuationAnalystAgent: ValuationAgencyPng,
  SentimentAnalystAgent: EmotionalAgencyPng,

  // System Agents
  TradingAgents: PortfolioManagerPng,
  SECAgent: SecAgentPng,
  NewsAgent: NewPushAgentPng,
};

export const VALUECELL_AGENT: AgentInfo = {
  agent_name: "ValueCellAgent",
  display_name: "ValueCell Agent",
  enabled: true,
  description:
    "ValueCell Agent is a super-agent that can help you manage different agents and tasks",
  created_at: TimeUtils.nowUTC().toISOString(),
  updated_at: TimeUtils.nowUTC().toISOString(),
  agent_metadata: {
    version: "1.0.0",
    author: "ValueCell",
    tags: ["valuecell", "super-agent"],
  },
};

export const MODEL_PROVIDERS = ["openrouter", "siliconflow"] as const;
export const MODEL_PROVIDER_MAP: Record<
  (typeof MODEL_PROVIDERS)[number],
  string[]
> = {
  openrouter: [
    "deepseek/deepseek-v3.1-terminus",
    "deepseek/deepseek-v3.2-exp",
    "qwen/qwen3-max",
    "openai/gpt-5-pro",
    "openai/gpt-5",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-haiku-4.5",
  ],
  siliconflow: ["deepseek-ai/DeepSeek-V3.2-Exp", "Qwen/Qwen3-235B-A22B"],
};

// Trading symbols options
export const TRADING_SYMBOLS: string[] = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "DOGE/USDT",
  "XRP/USDT",
];

// Strategy templates
export const STRATEGY_TEMPLATES = {
  default: {
    name: "Default",
    content: `Goal:
Produce steady, risk-aware crypto trading decisions that aim for consistent small gains while protecting capital.

Style & constraints:
- Focus on liquid major symbols (e.g., BTC-USD, ETH-USD). Avoid low-liquidity altcoins.
- Use conservative position sizing: target at most 1-2% of portfolio NAV per new trade (respecting \`cap_factor\`).
- Limit concurrent open positions to moderate number (use strategy config \`max_positions\`).
- Prefer market or tight-limit entries on pullbacks; avoid chasing large, fast moves.
- Use clear stop-loss and profit-target logic (see Risk Management section below).
- Favor trend-aligned entries: if the short- to mid-term trend is bullish, prefer long entries; if bearish, prefer shorts or sit out.
- Avoid entering during major macro events, maintenance windows, or low-volume periods (e.g., holidays, weekends depending on instrument).

Signals & decision heuristics:
- Trend detection: compute short EMA (e.g., 20) vs long EMA (e.g., 100). Require short EMA > long EMA for a bullish bias and vice versa for bearish bias.
- Momentum confirmation: require a momentum feature (e.g., RSI between 30-70 band moving toward oversold for entries) to avoid overbought entries.
- Volatility filter: if realized volatility in recent window is above a configurable threshold, reduce position size or skip signals.
- Pullback entries: prefer to enter on a pullback toward a moving average or a defined support zone rather than at local highs.
- Confluence: prefer signals with at least two confirming indicators (trend + momentum or trend + volume spike on breakout).

Order sizing & execution:
- Determine notional for a trade = min( cap_factor * average_symbol_daily_volume_notional, requested_notional, available buying power ).
- Convert notional -> quantity using current mark price.
- Clamp size to \`min_trade_qty\` and \`max_order_qty\` from runtime constraints.
- Use market orders for small/frequent rebalances; use limit orders (near current spread) for larger entries to avoid slippage.
- If partial fills occur, allow reattempts up to a short retry limit, then treat as partial fill and update portfolio accordingly.

Risk management (mandatory):
- Stop-loss: set a stop at a fixed percentage or ATR multiple (e.g., 1.5x ATR) below entry for longs (above for shorts).
- Take-profit: set a profit target at a risk:reward ratio of at least 1:1.5 (configurable).
- Trailing stop: optionally convert stop to trailing at meaningful profit thresholds (e.g., after 1x risk reached).
- Cap total portfolio risk: do not allow aggregated potential loss (sum of per-position risk) to exceed a configurable fraction of NAV.
- Fees: account for estimated fees when sizing orders and when evaluating profit/loss.

Position management & lifecycle:
- If a position is opened, compute and record entry price, notional, leverage, and planned stop/take levels in the trade meta.
- Re-evaluate open positions each cycle: if stop or take conditions hit, close; if market regime flips (trend opposite), consider reducing size or closing.
- Avoid frequent flipping: prefer 'flip-by-flat' — close an opposite-direction position fully before opening a new one (do not net opposite directions in same symbol).

Edge cases & guards:
- If the computed quantity is below \`min_trade_qty\`, skip the trade.
- If the current spread or slippage estimate is larger than an acceptable threshold, skip or reduce order size.
- If data for an instrument is stale (last candle older than 2x interval), skip trading that instrument this cycle.

Rationale and explainability:
- For each suggested action, include a short rationale string: why the signal triggered, which indicators agreed, and the planned stop/take.
- For rejected/ignored signals, include a brief reason (e.g., "skipped: notional below min_trade_qty", "skipped: volatility too high").

Telemetry & meta:
- Attach these meta fields to each instruction: compose_id, strategy_id, timestamp, estimated_fee, estimated_notional, confidence_score.
- Confidence: normalize to [0,1]; reduce size proportionally to confidence if below a threshold (e.g., 0.5).

Failure modes & safe-fallbacks:
- If execution gateway returns an error or rejects, do not keep trying indefinitely—mark instruction as ERROR and surface reason in logs and history.
- If critical internal errors occur, pause trading and emit a status update.

Summary (one-sentence):
Be conservative and trend-aware: take small, well-sized positions on pullbacks or confirmed breakouts, protect capital with explicit stops, and prefer gradual, repeatable profits over large, risky bets.

Examples (short):
- Bullish pullback: short EMA > long EMA, RSI dropped below 50 and turning up, enter long sized at 1% NAV, stop = 2% below entry, target = 3% above entry.
- Breakout: short EMA crosses above long EMA with volume spike, enter on a tight breakout candle close, stop under breakout low, R:R = 1:1.5.`,
  },
  aggressive: {
    name: "Aggressive",
    content: `Aggressive Trading Strategy

Overview
- Style: Aggressive momentum / breakout trader. High conviction, high turnover, uses leverage where available. Targets rapid capture of directional moves and volatility spikes.
- Objective: Maximize short-term returns by taking large, time-limited positions around breakouts, trend accelerations, and catalyst-driven moves. Accept higher drawdown and frequency of small losses for larger win potential.

Trading Regime & Timeframes
- Primary timeframes: 5m, 15m, 1h (entry/exit). Use 1m for micro-execution and slippage control when needed.
- Market types: Liquid equities, crypto, futures, or FX where tight spreads and sufficient depth exist.

Signals & Indicators
- Trend / Momentum:
  - EMA(8), EMA(21), EMA(50) for short-term trend alignment.
  - MACD(12,26,9) for momentum acceleration signals.
- Volatility / breakout:
  - ATR(14) for dynamic stop sizing and identifying volatility expansion.
  - Bollinger Bands (20, 2.0) for breakout confirmation.
- Confirmation:
  - Volume spike (current volume > 1.5x average) near breakout.
  - Price closing beyond recent consolidation (range breakout).

Entry Rules (Aggressive)
- Primary entry (breakout momentum):
  1. Price closes above the consolidation high (e.g., prior 20-period high) on 5m or 15m timeframe.
  2. EMA(8) > EMA(21) and EMA(21) > EMA(50) (trend alignment) OR MACD histogram > 0 and rising.
  3. Volume >= 1.5x average volume over the consolidation window OR ATR expansion > recent ATR.
  4. Enter with market or aggressive limit (tight) order sized per position-sizing rules below.

- Aggressive intraday add-on:
  - If momentum continues and price breaks a subsequent micro-high on 1m with supporting volume, add up to a fixed add-on fraction of initial position (scale-in). Respect max_position_qty.

Exit Rules
- Profit target: use a trailing stop based on ATR (e.g., trail = 1.5 * ATR(14)) or lock partial profits at predefined multiples (1st take: +1.5*ATR, scale out 25-50%).
- Hard stop: initial stop at entry_price - (stop_multiplier * ATR) for longs (reverse sign for shorts). Typical stop_multiplier=1.0–2.5 depending on aggressiveness.
- Time stop: exit any position that fails to reach profit target within a fixed time window (e.g., 6–12 candles on the entry timeframe).
- Flip / fast reversal: if the price rapidly reverses and crosses key EMAs in the opposite direction, flatten and consider re-entry in the new direction only if filters re-align.

Position Sizing & Risk
- Base risk per trade: aggressive (e.g., 1.0%–3.0% of account equity) per open position. Use higher risk when confidence is high.
- Leverage: allowed if product supports it, but cap net leverage at the trading_config.max_leverage.
- Scaling: initial entry = 60% of target position; add-ons up to 40% on confirmed continuation moves.
- Max exposure: enforce max_positions and max_position_qty constraints.
- Min notional: ensure each order meets minimum notional and exchange limits.

Execution & Slippage Control
- Use market orders when momentum is fast and limit orders when liquidity allows. Prefer immediate-or-cancel aggressive limits around breakouts.
- Respect quantity_step and exchange min increments.
- If slippage exceeds max_slippage_bps threshold repeatedly, reduce position sizing or widen stop targets.

Risk Controls & Guardrails
- Max concurrent positions: obey \`max_positions\` provided in trading config.
- Per-instrument max notional and position cap: obey \`max_position_qty\` and \`min_notional\`.
- Daily drawdown kill-switch: if daily drawdown > X% (configurable), stop new entries until manual review.
- Rate-limit entries to avoid overtrading during noise: minimum time between new full-size entries for the same symbol (e.g., 15m).

Parameters (example defaults)
- EMA periods: 8, 21, 50
- MACD: 12,26,9
- ATR period: 14
- Stop multiplier: 1.5
- Trail multiplier: 1.5
- Volume spike multiplier: 1.5
- Initial size fraction: 0.6 (60%)
- Add-on fraction: 0.4 (40%)
- Time stop window: 12 candles

Operational Notes
- Backtest thoroughly across market regimes (bull, bear, sideways) and on multiple symbols before live deployment.
- Use paper trading first; expect frequent small losses and occasional large gains.
- Log all entries/exits with reasons (signal that triggered, indicators values, volume) for post-trade analysis and strategy tuning.`,
  },
  conservative: {
    name: "Conservative",
    content: `Conservative Trading Strategy

Overview
- Style: Ultra-conservative, capital preservation focused. Extremely low risk tolerance. Prioritizes avoiding losses over maximizing gains.
- Objective: Maintain and slowly grow capital through highly selective, low-risk entries with very tight risk controls. Accept very low returns for near-zero drawdown.

Trading Regime & Timeframes
- Primary timeframes: 1h, 4h, 1d (entry/exit). Avoid intraday volatility and prefer stable, trending markets.
- Market types: Only the most liquid, established assets with deep order books and minimal manipulation risk.

Signals & Indicators
- Trend / Momentum:
  - EMA(50), EMA(200) for long-term trend alignment only.
  - RSI(14) kept strictly within 40-60 range.
- Volatility / breakout:
  - ATR(20) used conservatively for stop placement only.
  - Avoid breakouts; prefer consolidation entries only.
- Confirmation:
  - Volume must be stable (within 0.8-1.2x average).
  - Price must be within established trend channels.

Entry Rules (Ultra-Conservative)
- Primary entry (trend continuation only):
  1. EMA(50) > EMA(200) and current price > EMA(50) (strong uptrend only).
  2. RSI between 45-55 (neutral momentum).
  3. Volume stable (0.9-1.1x 20-period average).
  4. Price must be in a clear uptrend channel without recent volatility spikes.
  5. Enter only on pullbacks to EMA(50) support.

- No add-ons or scaling: single entry only, no position building.

Exit Rules
- Profit target: very conservative 1:1 risk-reward ratio only.
- Hard stop: extremely tight - 0.5% below entry for longs.
- Time stop: exit after 5-10 days if no profit target hit.
- Any adverse price movement triggers immediate exit.

Position Sizing & Risk
- Base risk per trade: minimal (0.1%-0.3% of account equity).
- Leverage: none or minimal (1x only).
- Max exposure: 1 position maximum at any time.
- Min notional: standard exchange minimums only.

Execution & Slippage Control
- Use limit orders only, placed conservatively.
- Never use market orders.
- If any slippage occurs, cancel and re-evaluate.

Risk Controls & Guardrails
- Max concurrent positions: 1 only.
- Daily drawdown limit: 0.1% maximum.
- Weekly drawdown limit: 0.5% maximum.
- Monthly drawdown limit: 1.0% maximum.
- Stop trading immediately if any limit breached.

Parameters (ultra-conservative defaults)
- EMA periods: 50, 200
- RSI period: 14, range: 45-55
- ATR period: 20
- Stop loss: 0.5%
- Profit target: 1:1 ratio
- Max holding time: 10 days
- Volume stability: 0.9-1.1x average

Operational Notes
- This strategy may have very low returns but virtually eliminates risk.
- Suitable for capital preservation during uncertain market conditions.
- Requires extreme patience and discipline.`,
  },
} as const;

export type StrategyTemplateId = keyof typeof STRATEGY_TEMPLATES;
