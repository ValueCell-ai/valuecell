import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { apiClient } from "@/lib/api-client";

export interface Stock {
  id: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface WatchlistItem extends Stock {
  addedAt: string;
}

// Get watchlist - requires authentication
export const useGetWatchlist = () =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.watchlist,
    queryFn: (): Promise<WatchlistItem[]> =>
      apiClient.get<WatchlistItem[]>("watchlist"),
  });

// Add stock to watchlist - requires authentication
export const useAddStockToWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stock: Stock): Promise<WatchlistItem> =>
      apiClient.post<WatchlistItem>("watchlist", stock),
    onSuccess: (newStock) => {
      // Optimistic update: immediately update cache
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.watchlist,
        (old: WatchlistItem[] = []) => [...old, newStock],
      );

      // Also update status in stock list (if exists)
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.stocksList,
        (old: Stock[] = []) =>
          old.map((s) =>
            s.id === newStock.id ? { ...s, inWatchlist: true } : s,
          ),
      );
    },
    onError: (error) => {
      console.error("Failed to add stock to watchlist:", error);
    },
  });
};

// Get stocks list - public API, no authentication required
export const useGetStocksList = () =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stocksList,
    queryFn: (): Promise<Stock[]> =>
      apiClient.get<Stock[]>("stocks", { requiresAuth: false }),
    staleTime: 10 * 60 * 1000, // Extended fresh time for public data
    gcTime: 60 * 60 * 1000, // Extended garbage collection time
  });

// Remove stock from watchlist - requires authentication
export const useRemoveStockFromWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stockId: string): Promise<void> =>
      apiClient.delete<void>(`watchlist/${stockId}`),
    onSuccess: (_, deletedStockId) => {
      // Optimistic update: remove from cache
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.watchlist,
        (old: WatchlistItem[] = []) =>
          old.filter((stock) => stock.id !== deletedStockId),
      );

      // Also update status in stock list
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.stocksList,
        (old: Stock[] = []) =>
          old.map((s) =>
            s.id === deletedStockId ? { ...s, inWatchlist: false } : s,
          ),
      );
    },
    onError: (error) => {
      console.error("Failed to remove stock from watchlist:", error);
    },
  });
};

// Get stock detail - public API
export const useGetStockDetail = (stockId: string) =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stockDetail(stockId),
    queryFn: (): Promise<Stock> =>
      apiClient.get<Stock>(`stocks/${stockId}`, { requiresAuth: false }),
    enabled: !!stockId, // Only execute query when stockId exists
    staleTime: 2 * 60 * 1000, // Shorter fresh time for real-time stock data
    retry: 1, // Fewer retries for detail queries
  });

// Search stocks - public API
export const useSearchStocks = (query: string, enabled: boolean = true) =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stockSearch(query),
    queryFn: (): Promise<Stock[]> =>
      apiClient.get<Stock[]>(`stocks/search?q=${encodeURIComponent(query)}`, {
        requiresAuth: false,
      }),
    enabled: enabled && query.length >= 2, // Search only with at least 2 characters
    gcTime: 15 * 60 * 1000, // Extended cache time for search results
    retry: 1, // Fewer retries for search queries
  });

// Batch operation: batch add to watchlist
export const useBatchAddToWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (stocks: Stock[]): Promise<WatchlistItem[]> =>
      apiClient.post<WatchlistItem[]>("watchlist/batch", { stocks }),
    onSuccess: (newStocks) => {
      // Optimistic update: batch add to cache
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.watchlist,
        (old: WatchlistItem[] = []) => [...old, ...newStocks],
      );

      // Update stock list status
      const newStockIds = new Set(newStocks.map((s) => s.id));
      queryClient.setQueryData(
        API_QUERY_KEYS.STOCK.stocksList,
        (old: Stock[] = []) =>
          old.map((s) =>
            newStockIds.has(s.id) ? { ...s, inWatchlist: true } : s,
          ),
      );
    },
    onError: (error) => {
      console.error("Failed to batch add to watchlist:", error);
    },
  });
};
