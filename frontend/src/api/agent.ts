import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { VALUECELL_AGENT } from "@/constants/agent";
import { API_QUERY_KEYS } from "@/constants/api";
import { type ApiResponse, apiClient } from "@/lib/api-client";
import type { AgentInfo } from "@/types/agent";

export const useGetAgentInfo = (params: { agentName: string }) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.AGENT.agentInfo(Object.values(params)),
    queryFn: async () => {
      // Return hardcoded data for ValueCellAgent
      if (params.agentName === "ValueCellAgent") {
        return Promise.resolve({ data: VALUECELL_AGENT });
      }
      // Fetch from API for other agents
      return apiClient.get<ApiResponse<AgentInfo>>(
        `/agents/by-name/${params.agentName}`,
      );
    },
    select: (data) => data.data,
  });
};

export const useGetAgentList = (
  params: { enabled_only: string } = { enabled_only: "false" },
) => {
  return useQuery({
    queryKey: API_QUERY_KEYS.AGENT.agentList(Object.values(params)),
    queryFn: () =>
      apiClient.get<ApiResponse<{ agents: AgentInfo[] }>>(
        `/agents/?enabled_only=${params.enabled_only}`,
      ),
    select: (data) => data.data.agents,
  });
};

export const useEnableAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { agentName: string; enabled: boolean }) =>
      apiClient.post<ApiResponse<null>>(`/agents/${params.agentName}/enable`, {
        enabled: params.enabled,
      }),
    onSuccess: (_, { agentName }) => {
      // invalidate agent list query cache to trigger re-fetch
      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.AGENT.agentInfo([agentName]),
      });

      queryClient.invalidateQueries({
        queryKey: API_QUERY_KEYS.AGENT.agentList([]),
      });
    },
  });
};
