import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { CreateStrategyRequest, Strategy, Trade } from "@/types/strategy";

export const useGetStrategyList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
    queryFn: () =>
      apiClient.get<
        ApiResponse<{
          strategies: Strategy[];
        }>
      >("/strategies"),
    select: (data) => data.data.strategies,
  });
};

export const useGetStrategyTrades = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyTrades([strategyId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<Trade[]>>(
        `/strategies/detail?id=${strategyId}`,
      ),
    select: (data) => data.data,
    enabled: !!strategyId,
  });
};

export const useCreateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateStrategyRequest) =>
      apiClient.post<ApiResponse<{ strategy_id: string }>>(
        "/create_strategy_agent",
        data,
      ),
    onSuccess: () => {
      // Invalidate strategy list to refetch
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
      });
    },
  });
};
