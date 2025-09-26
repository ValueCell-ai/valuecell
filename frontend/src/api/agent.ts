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

export const useGetAgentList = (params?: { enabled_only: boolean }) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.AGENT.agentList,
    queryFn: () =>
      apiClient.get<ApiResponse<{ agents: AgentInfo[] }>>(
        `/agents?enabled_only=${params?.enabled_only || false}`,
      ),
    select: (data) => data.data.agents,
  });
};
