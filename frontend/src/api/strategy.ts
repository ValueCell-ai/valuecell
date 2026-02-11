import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type {
  BacktestConfig,
  BacktestResult,
  CreateStrategy,
  ManualClosePositionData,
  ManualClosePositionRequest,
  MarketStateAndScores,
  PortfolioSummary,
  Position,
  PositionControlUpdate,
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
      >("/strategies/"),
    select: (data) => data.data.strategies,
    refetchInterval: 5 * 1000,
  });
};

export const useGetStrategyDetails = (strategyId?: number) => {
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

export const useGetStrategyHoldings = (strategyId?: number) => {
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

export const useGetStrategyPriceCurve = (strategyId?: number) => {
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

export const useGetStrategyPortfolioSummary = (strategyId?: number) => {
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
    mutationFn: (data: CreateStrategy) =>
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

export const useStartStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) =>
      apiClient.post<ApiResponse<{ message: string }>>(
        `/strategies/start?id=${strategyId}`,
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
    mutationFn: (data: CreateStrategy["exchange_config"]) =>
      apiClient.post<ApiResponse<null>>("/strategies/test-connection", data),
  });
};

export const useStopStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: number) =>
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
    mutationFn: (strategyId: number) =>
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

// Dynamic Strategy APIs
export const useGetMarketStateAndScores = (
  symbol?: string,
  baseStrategies?: string,
  riskMode?: string,
  exchangeId?: string,
) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.marketStateAndScores([
      symbol ?? "",
      baseStrategies ?? "",
      riskMode ?? "",
      exchangeId ?? "",
    ]),
    queryFn: () => {
      const params = new URLSearchParams();
      if (symbol) params.append("symbol", symbol);
      if (baseStrategies) params.append("base_strategies", baseStrategies);
      if (riskMode) params.append("risk_mode", riskMode);
      if (exchangeId) params.append("exchange_id", exchangeId);

      return apiClient.get<ApiResponse<MarketStateAndScores>>(
        `/strategies/dynamic/scores?${params.toString()}`,
      );
    },
    select: (data) => data.data,
    enabled: !!symbol, // 只有当 symbol 存在时才启用查询
    refetchInterval: 30 * 1000, // 每30秒刷新一次
  });
};

// Backtest APIs
export const useRunBacktest = () => {
  return useMutation({
    mutationFn: (config: BacktestConfig) =>
      apiClient.post<ApiResponse<{ backtestId: string }>>(
        "/strategies/backtest/run",
        config,
      ),
  });
};

export const useGetBacktestResult = (backtestId?: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.backtestResult([backtestId ?? ""]),
    queryFn: () =>
      apiClient.get<ApiResponse<BacktestResult>>(
        `/strategies/backtest/result?id=${backtestId}`,
      ),
    select: (data) => data.data,
    enabled: !!backtestId,
    refetchInterval: 5 * 1000, // 回测进行中时每5秒刷新
  });
};

// Position Control APIs
export const useUpdatePositionControl = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PositionControlUpdate) =>
      apiClient.post<ApiResponse<{ message: string }>>(
        "/strategies/position-control/update",
        data,
      ),
    onSuccess: (_, variables) => {
      // 刷新策略列表和持仓信息
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
      });
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyHoldings([variables.strategyId]),
      });
    },
  });
};

export const useDeleteStrategyPrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (promptId: string) =>
      apiClient.delete<
        ApiResponse<{ deleted: boolean; prompt_id: string; message: string }>
      >(`/strategies/prompts/${promptId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyPrompts,
      });
    },
  });
};

export const useStrategyPerformance = (strategyId: number | null) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.STRATEGY.strategyPerformance(
      strategyId ? [strategyId] : [],
    ),
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyPerformance>>(
        `/strategies/performance?id=${strategyId}`,
      ),
    select: (data) => data.data,
    enabled: false,
  });
};

// Manual Close Position API
export const useManualClosePosition = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ManualClosePositionRequest) =>
      apiClient.post<ApiResponse<ManualClosePositionData>>(
        "/strategies/close_position",
        data,
      ),
    onSuccess: (_, variables) => {
      // 刷新策略列表和持仓信息
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyList,
      });
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.STRATEGY.strategyHoldings([
          variables.strategyId,
        ]),
      });
    },
  });
};

