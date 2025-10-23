import { useQuery } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { ConversationList } from "@/types/conversation";

export const useGetConversationList = () => {
  return useQuery({
    queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
    queryFn: () =>
      apiClient.get<ApiResponse<ConversationList>>("/conversations"),
    select: (data) => data.data.conversations,
  });
};
