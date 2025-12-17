import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { API_QUERY_KEYS, VALUECELL_BACKEND_URL } from "@/constants/api";
import i18n from "@/i18n";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import { useLanguage } from "@/store/settings-store";
import { useSystemStore } from "@/store/system-store";
import type {
  StrategyDetail,
  StrategyRankItem,
  StrategyReport,
  SystemInfo,
} from "@/types/system";

export interface DefaultTicker {
  ticker: string;
  symbol: string;
  name: string;
}

export interface DefaultTickersResponse {
  region: string;
  tickers: DefaultTicker[];
}

export const useBackendHealth = () => {
  return useQuery({
    queryKey: ["backend-health"],
    queryFn: () => apiClient.get<boolean>("/healthz"),
    retry: false,
    refetchInterval: (query) => {
      return query.state.status === "error" ? 2000 : 10000;
    },
    refetchOnWindowFocus: true,
  });
};

export const getUserInfo = async (token: string) => {
  const { data } = await apiClient.get<
    ApiResponse<Omit<SystemInfo, "access_token" | "refresh_token">>
  >(`${VALUECELL_BACKEND_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data;
};

export const useSignOut = () => {
  return useMutation({
    mutationFn: () =>
      apiClient.post<ApiResponse<void>>(
        `${VALUECELL_BACKEND_URL}/auth/logout`,
        null,
        {
          requiresAuth: true,
        },
      ),

    onSuccess: () => {
      useSystemStore.getState().clearSystemInfo();
    },
    onError: (error) => {
      toast.error(JSON.stringify(error));
      useSystemStore.getState().clearSystemInfo();
    },
  });
};

export const useGetStrategyList = (
  params: { limit: number; days: number } = { limit: 10, days: 7 },
) => {
  const language = useLanguage();

  return useQuery({
    queryKey: API_QUERY_KEYS.SYSTEM.strategyList([
      ...Object.values(params),
      language,
    ]),
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyRankItem[]>>(
        `${VALUECELL_BACKEND_URL}/strategy/list?limit=${params.limit}&days=${params.days}&language=${language}`,
      ),
    select: (data) => data.data,
  });
};

export const useGetStrategyDetail = (id: number | null) => {
  const language = useLanguage();

  return useQuery({
    queryKey: API_QUERY_KEYS.SYSTEM.strategyDetail([id ?? "", language]),
    queryFn: () =>
      apiClient.get<ApiResponse<StrategyDetail>>(
        `${VALUECELL_BACKEND_URL}/strategy/detail/${id}?language=${language}`,
      ),
    select: (data) => data.data,
    enabled: !!id,
  });
};

export const usePublishStrategy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: StrategyReport) => {
      return apiClient.post<ApiResponse<void>>(
        `${VALUECELL_BACKEND_URL}/strategy/report`,
        data,
        {
          requiresAuth: true,
        },
      );
    },
    onSuccess: () => {
      toast.success(i18n.t("strategy.toast.published"));
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SYSTEM.strategyList([]),
      });
    },
    onError: (error) => {
      toast.error(JSON.stringify(error));
    },
  });
};

/**
 * Get region-aware default tickers for homepage display.
 * Returns A-share indices for China mainland users,
 * global indices for other regions.
 *
 * @param region - Optional region override for testing (e.g., "cn" or "default").
 *                 In development, you can set this to test different regions.
 */
export const useGetDefaultTickers = (region?: string) => {
  const language = useLanguage();

  return useQuery({
    queryKey: ["system", "default-tickers", region, language],
    queryFn: () => {
      const regionParam = region ? `region=${region}` : "";
      const langParam = `language=${language}`;
      const params = [regionParam, langParam].filter(Boolean).join("&");

      return apiClient.get<ApiResponse<DefaultTickersResponse>>(
        `system/default-tickers?${params}`,
      );
    },
    select: (data) => data.data,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour, region doesn't change frequently
  });
};
