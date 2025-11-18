export type MemoryItem = {
  id: number;
  content: string;
};

export type ModelProvider = {
  provider: string;
};

export type ProviderModelInfo = {
  model_id: string;
  model_name: string;
};

export type ProviderDetail = {
  api_key: string;
  api_key_url: string;
  base_url: string;
  is_default: boolean;
  default_model_id: string;
  models: ProviderModelInfo[];
};
