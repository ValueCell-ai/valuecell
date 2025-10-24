import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import type { ApiResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import type { MemoryItem } from "@/types/setting";

export const useGetMemoryList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.SETTING.memoryList,
    queryFn: () =>
      apiClient.get<ApiResponse<{ profiles: MemoryItem[] }>>("/user/profile"),
    select: (data) => data.data.profiles,
  });
};

export const useRemoveMemory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (profile_id: MemoryItem["id"]) =>
      apiClient.delete<ApiResponse<null>>(`/user/profile/${profile_id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.memoryList,
      });
    },
  });
};
