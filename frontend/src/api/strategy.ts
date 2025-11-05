import { useQuery } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { Strategy } from "@/types/strategy";

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
