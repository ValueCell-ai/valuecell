import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { VALUECELL_BACKEND_URL } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import { useSystemStore } from "@/store/system-store";
import type {
  StrategyDetail,
  StrategyRankItem,
  SystemInfo,
} from "@/types/system";

export const useBackendHealth = () => {
  return useQuery({
    queryKey: ["backend-health"],
    queryFn: () =>
      apiClient.get<boolean>("/healthz", {
        requiresAuth: false,
      }),
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

export const useGetStrategyList = (limit: number = 10, days: number = 7) => {
  return useQuery({
    queryKey: ["strategy-list", limit, days],
    queryFn: async () => {
      const data = await apiClient.get<StrategyRankItem[]>(
        `/strategy/list?limit=${limit}&days=${days}`,
      );
      return data;
    },
  });
};

export const useGetStrategyDetail = (id: number | null) => {
  return useQuery({
    queryKey: ["strategy-detail", id],
    queryFn: async () => {
      if (!id) return null;
      const data = await apiClient.get<StrategyDetail>(
        `/strategy/detail/${id}`,
      );
      return data;
    },
    enabled: !!id,
  });
};
