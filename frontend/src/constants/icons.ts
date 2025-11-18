import {
  AzurePng,
  BinancePng,
  BtcPng,
  DeepSeekPng,
  DogePng,
  EthPng,
  GooglePng,
  OkxPng,
  OpenAiCompatiblePng,
  OpenAiPng,
  OpenRouterPng,
  SiliconFlowPng,
  SolPng,
  XrpPng,
} from "@/assets/png";

export const MODEL_PROVIDER_ICONS = {
  openrouter: OpenRouterPng,
  siliconflow: SiliconFlowPng,
  openai: OpenAiPng,
  "openai-compatible": OpenAiCompatiblePng,
  deepseek: DeepSeekPng,
  google: GooglePng,
  azure: AzurePng,
};

export const EXCHANGE_ICONS = {
  binance: BinancePng,
  okx: OkxPng,
};

export const SYMBOL_ICONS = {
  "BTC/USDT": BtcPng,
  "ETH/USDT": EthPng,
  "SOL/USDT": SolPng,
  "DOGE/USDT": DogePng,
  "XRP/USDT": XrpPng,
};
