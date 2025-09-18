// API Query keys constants

const STOCK_QUERY_KEYS = {
  watchlist: ["watchlist"],
  stocksList: ["stocksList"],
  stockDetail: (id: string) => ["stock", "detail", id] as const,
  stockSearch: (query: string) => ["stock", "search", query] as const,
} as const;

export const API_QUERY_KEYS = {
  STOCK: STOCK_QUERY_KEYS,
} as const;
