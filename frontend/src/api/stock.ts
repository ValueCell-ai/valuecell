import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS, USER_LANGUAGE } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { Stock, StockHistory, StockPrice, Watchlist } from "@/types/stock";

export const useGetWatchlist = () =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.watchlist,
    queryFn: () => apiClient.get<ApiResponse<Watchlist[]>>("watchlist"),
    select: (data) => data.data,
  });

export const useGetStocksList = (params: { query: string }) =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stockSearch(Object.values(params)),
    queryFn: ({ signal }) =>
      apiClient.get<ApiResponse<{ results: Stock[] }>>(
        `watchlist/asset/search?q=${params.query}&language=${USER_LANGUAGE}`,
        { signal },
      ),
    select: (data) => data.data.results,
    enabled: !!params.query,
  });

export const useAddStockToWatchlist = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticker: Pick<Stock, "ticker">) =>
      apiClient.post<ApiResponse<null>>("watchlist/stocks", ticker),
    onSuccess: () => {
      // invalidate watchlist query cache to trigger re-fetch
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STOCK.watchlist,
      });
    },
  });
};

export const useGetStockPrice = (params: { ticker: string }) =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stockPrice(Object.values(params)),
    queryFn: () =>
      apiClient.get<ApiResponse<StockPrice>>(
        `watchlist/asset/${params.ticker}/price`,
      ),
    select: (data) => data.data,
    enabled: !!params.ticker,
  });

export const useGetStockHistory = (params: { ticker: string }) =>
  useQuery({
    queryKey: API_QUERY_KEYS.STOCK.stockHistory(Object.values(params)),
    queryFn: () =>
      apiClient.get<ApiResponse<{ results: StockHistory[] }>>(
        `watchlist/asset/${params.ticker}/price/historical`,
      ),
  });
