import { useQuery } from "@tanstack/react-query";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { AgentInfo } from "@/types/agent";

export const useGetAgentInfo = (params: { agentName: string }) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.AGENT.agentInfo(Object.values(params)),
    queryFn: () =>
      apiClient.get<ApiResponse<AgentInfo>>(
        `/agents/by-name/${params.agentName}`,
      ),
    select: (data) => data.data,
  });
};
