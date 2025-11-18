import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import type { ApiResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import type {
  MemoryItem,
  ModelProvider,
  ProviderDetail,
  ProviderModelInfo,
} from "@/types/setting";

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

export const useGetModelProviders = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.SETTING.modelProviders,
    queryFn: () =>
      apiClient.get<ApiResponse<ModelProvider[]>>("/models/providers"),
    select: (data) => data.data,
  });
};

export const useGetModelProviderDetail = (provider: string | undefined) => {
  return useQuery({
    enabled: !!provider,
    queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail(
      provider ? [provider] : [],
    ),
    queryFn: () =>
      apiClient.get<ApiResponse<ProviderDetail>>(
        `/models/providers/${provider}`,
      ),
    select: (data) => data.data,
  });
};

export const useUpdateProviderConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: {
      provider: string;
      api_key?: string;
      base_url?: string;
    }) =>
      apiClient.put<ApiResponse<null>>(
        `/models/providers/${params.provider}/config`,
        {
          api_key: params.api_key,
          base_url: params.base_url,
        },
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([
          variables.provider,
        ]),
      });
    },
  });
};

export const useAddProviderModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: {
      provider: string;
      model_id: string;
      model_name: string;
    }) =>
      apiClient.post<ApiResponse<ProviderModelInfo>>(
        `/models/providers/${params.provider}/models`,
        {
          model_id: params.model_id,
          model_name: params.model_name,
        },
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([
          variables.provider,
        ]),
      });
    },
  });
};

export const useDeleteProviderModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { provider: string; model_id: string }) =>
      apiClient.delete<ApiResponse<null>>(
        `/models/providers/${params.provider}/models?model_id=${encodeURIComponent(params.model_id)}`,
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([
          variables.provider,
        ]),
      });
    },
  });
};

export const useSetDefaultProvider = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { provider: string }) =>
      apiClient.put<ApiResponse<null>>("/models/providers/default", {
        provider: params.provider,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviders,
      });
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([]),
      });
    },
  });
};

export const useSetDefaultProviderModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { provider: string; model_id: string }) =>
      apiClient.put<ApiResponse<null>>(
        `/models/providers/${params.provider}/default-model`,
        {
          model_id: params.model_id,
        },
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([
          variables.provider,
        ]),
      });
    },
  });
};
