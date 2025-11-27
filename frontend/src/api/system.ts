import { useQuery } from "@tanstack/react-query";
import { VALUECELL_BACKEND_URL } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import { useSystemAccessToken } from "@/store/system-store";
import type { SystemInfo } from "@/types/system";

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

export const useGetUserInfo = () => {
  return useQuery({
    queryKey: ["user-info"],
    queryFn: () =>
      apiClient.get<
        ApiResponse<{
          user: Omit<SystemInfo, "accessToken" | "refreshToken">;
        }>
      >(`${VALUECELL_BACKEND_URL}/auth/me`, {
        requiresAuth: true,
      }),
    select: (data) => data.data.user,
    enabled: !!useSystemAccessToken(),
  });
};
