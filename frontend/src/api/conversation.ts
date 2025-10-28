import { useQuery } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type {
  ConversationHistory,
  ConversationList,
} from "@/types/conversation";

export const useGetConversationList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationList>>("/conversations"),
    select: (data) => data.data.conversations,
  });
};

export const useGetConversationHistory = (conversationId: string) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationHistory([conversationId]),
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationHistory>>(
        `/conversations/${conversationId}/history`,
      ),
    select: (data) => data.data.items,
    enabled: !!conversationId,
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
    refetchInterval: 30 * 1000,
    enabled: !!conversationId,
  });
};
