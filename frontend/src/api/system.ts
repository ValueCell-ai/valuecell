import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

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
