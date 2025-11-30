import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type {
  CreateStrategyRequest,
  PortfolioSummary,
  Position,
  Strategy,
  StrategyCompose,
  StrategyPerformance,
  StrategyPrompt,
} from "@/types/strategy";

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
    refetchInterval: 5 * 1000,
  });
};

export const useGetStrategyDetails = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyTrades([strategyId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyCompose[]>>(
        `/strategies/detail?id=${strategyId}`,
      ),
    select: (data) => data.data,
    refetchInterval: 5 * 1000,
    enabled: !!strategyId,
  });
};

export const useGetStrategyHoldings = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyHoldings([strategyId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<Position[]>>(
        `/strategies/holding?id=${strategyId}`,
      ),
    select: (data) => data.data,
    refetchInterval: 5 * 1000,
    enabled: !!strategyId,
  });
};

export const useGetStrategyPriceCurve = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyPriceCurve([strategyId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<Array<Array<string | number>>>>(
        `/strategies/holding_price_curve?id=${strategyId}`,
      ),
    select: (data) => data.data,
    refetchInterval: 5 * 1000,
    enabled: !!strategyId,
  });
};

export const useGetStrategyPortfolioSummary = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyPortfolioSummary([
      strategyId ?? "",
    ]),
    queryFn: () =>
      apiClient.get<ApiResponse<PortfolioSummary>>(
        `/strategies/portfolio_summary?id=${strategyId}`,
      ),
    select: (data) => data.data,
    refetchInterval: 5 * 1000,
    enabled: !!strategyId,
  });
};

export const useCreateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateStrategyRequest) =>
      apiClient.post<ApiResponse<{ strategy_id: string }>>(
        "/strategies/create",
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

export const useTestConnection = () => {
  return useMutation({
    mutationFn: (data: CreateStrategyRequest["exchange_config"]) =>
      apiClient.post<ApiResponse<null>>("/strategies/test-connection", data),
  });
};

export const useStopStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) =>
      apiClient.post<ApiResponse<{ message: string }>>(
        `/strategies/stop?id=${strategyId}`,
      ),
    onSuccess: () => {
      // Invalidate strategy list to refetch
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
      });
    },
  });
};

export const useDeleteStrategy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (strategyId: string) =>
      apiClient.delete<ApiResponse<null>>(
        `/strategies/delete?id=${strategyId}`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
      });
    },
  });
};

export const useGetStrategyPrompts = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyPrompts,
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyPrompt[]>>("/strategies/prompts"),
    select: (data) => data.data,
    staleTime: 0,
  });
};

export const useCreateStrategyPrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Pick<StrategyPrompt, "name" | "content">) =>
      apiClient.post<ApiResponse<StrategyPrompt>>(
        "/strategies/prompts/create",
        data,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyPrompts,
      });
    },
  });
};

export const useStrategyPerformance = (strategyId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyPerformance([strategyId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyPerformance>>(
        `/strategies/performance?id=${strategyId}`,
      ),
    select: (data) => data.data,
    enabled: false,
  });
};
