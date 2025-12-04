import { z } from "zod";

export const aiModelSchema = z.object({
  provider: z.string().min(1, "Model platform is required"),
  model_id: z.string().min(1, "Model selection is required"),
  api_key: z.string().min(1, "API key is required"),
});

const baseStep2Fields = {
  exchange_id: z.string(),
  api_key: z.string(),
  secret_key: z.string(),
  passphrase: z.string(),
  wallet_address: z.string(),
  private_key: z.string(),
};

// Step 2 Schema: Exchanges (conditional validation with superRefine)
export const exchangeSchema = z.union([
  // Virtual Trading
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("virtual"),
  }),

  // Live Trading - Hyperliquid
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.literal("hyperliquid"),
    wallet_address: z
      .string()
      .min(1, "Wallet Address is required for Hyperliquid"),
    private_key: z.string().min(1, "Private Key is required for Hyperliquid"),
  }),

  // Live Trading - OKX & Coinbase (Require Passphrase)
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.enum(["okx", "coinbaseexchange"]),
    api_key: z.string().min(1, "API key is required"),
    secret_key: z.string().min(1, "Secret key is required"),
    passphrase: z.string().min(1, "Passphrase is required"),
  }),

  // Live Trading - Standard Exchanges
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.enum(["binance", "blockchaincom", "gate", "mexc"]),
    api_key: z.string().min(1, "API key is required"),
    secret_key: z.string().min(1, "Secret key is required"),
  }),
]);

// Step 3 Schema: Trading Strategy
export const tradingStrategySchema = z.object({
  strategy_type: z.enum(["PromptBasedStrategy", "GridStrategy"]),
  strategy_name: z.string().min(1, "Strategy name is required"),
  initial_capital: z.number().min(1, "Initial capital must be at least 1"),
  max_leverage: z
    .number()
    .min(1, "Leverage must be at least 1")
    .max(5, "Leverage must be at most 5"),
  symbols: z.array(z.string()).min(1, "At least one symbol is required"),
  template_id: z.string().min(1, "Template selection is required"),
  decide_interval: z
    .number()
    .min(10, "Interval must be at least 10 seconds")
    .max(3600, "Interval must be at most 3600 seconds"),
});

export const copyTradingStrategySchema = z.object({
  strategy_name: z.string().min(1, "Strategy name is required"),
  initial_capital: z.number().min(1, "Initial capital must be at least 1"),
  max_leverage: z
    .number()
    .min(1, "Leverage must be at least 1")
    .max(5, "Leverage must be at most 5"),
  symbols: z.array(z.string()).min(1, "At least one symbol is required"),
  decide_interval: z
    .number()
    .min(10, "Interval must be at least 10 seconds")
    .max(3600, "Interval must be at most 3600 seconds"),
  strategy_type: z.enum(["PromptBasedStrategy", "GridStrategy"]),
  prompt_name: z.string().min(1, "Prompt name is required"),
  prompt: z.string().min(1, "Prompt is required"),
});
