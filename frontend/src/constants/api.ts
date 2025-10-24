// API Query keys constants

export const queryKeyFn = (defaultKey: string[]) => (queryKey: string[]) => [
  ...defaultKey,
  ...queryKey,
];

const STOCK_QUERY_KEYS = {
  watchlist: ["watch"],
  stockList: ["stock"],
  stockDetail: queryKeyFn(["stock", "detail"]),
  stockSearch: queryKeyFn(["stock", "search"]),
  stockPrice: queryKeyFn(["stock", "price"]),
  stockHistory: queryKeyFn(["stock", "history"]),
} as const;

const AGENT_QUERY_KEYS = {
  agentList: queryKeyFn(["agent", "list"]),
  agentInfo: queryKeyFn(["agent", "info"]),
  conversationList: ["conversation"],
} as const;

export const CONVERSATION_QUERY_KEYS = {
  conversationList: ["conversation"],
  conversationHistory: queryKeyFn(["conversation", "history"]),
} as const;

export const SETTING_QUERY_KEYS = {
  memoryList: ["memory"],
} as const;

export const API_QUERY_KEYS = {
  STOCK: STOCK_QUERY_KEYS,
  AGENT: AGENT_QUERY_KEYS,
  CONVERSATION: CONVERSATION_QUERY_KEYS,
  SETTING: SETTING_QUERY_KEYS,
} as const;

/**
 * Temporary language setting
 * @description This is a temporary language setting for the API.
 */
export const USER_LANGUAGE = "en-US";
