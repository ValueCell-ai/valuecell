import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type {
  ConversationHistory,
  ConversationList,
  TaskCardItem,
} from "@/types/conversation";

export const useGetConversationList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationList>>("/conversations"),
    select: (data) => data.data.conversations,
  });
};

export const useGetConversationHistory = (
  conversationId: string,
  deps: boolean[] = [],
) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationHistory([conversationId]),
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationHistory>>(
        `/conversations/${conversationId}/history`,
      ),
    select: (data) => data.data.items,
    enabled: !!conversationId && deps.every((dep) => dep),
    staleTime: 0,
  });
};

export const useDeleteConversation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) =>
      apiClient.delete<ApiResponse<null>>(`/conversations/${conversationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
      });
    },
  });
};

export const usePollTaskList = (conversationId: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationTaskList([
      conversationId,
    ]),
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationHistory>>(
        `/conversations/${conversationId}/scheduled-task-results`,
      ),
    select: (data) => data.data.items,
    refetchInterval: 60 * 1000,
    enabled: !!conversationId,
  });
};

export const useAllPollTaskList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.allConversationTaskList,
    queryFn: () =>
      apiClient.get<ApiResponse<{ agents: TaskCardItem[] }>>(
        `/conversations/scheduled-task-results`,
      ),
    select: (data) => data.data.agents,
    refetchInterval: 60 * 1000,
  });
};

export const useCancelTask = () => {
  return useMutation({
    mutationFn: (task_id: string) =>
      apiClient.post<ApiResponse<null>>(`/tasks/${task_id}/cancel`),
  });
};
