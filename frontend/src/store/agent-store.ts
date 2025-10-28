import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/shallow";
import {
  batchUpdateAgentConversationsStore,
  updateAgentConversationsStore,
} from "@/lib/agent-store";
import type { AgentConversationsStore, SSEData } from "@/types/agent";

interface AgentStoreState {
  agentStore: AgentConversationsStore;
  curConversationId: string;
  dispatchAgentStore: (action: SSEData) => void;
  dispatchAgentStoreHistory: (
    conversationId: string,
    history: SSEData[],
    clearHistory?: boolean,
  ) => void;
  setCurConversationId: (conversationId: string) => void;
  resetStore: () => void;
}

const INITIAL = { agentStore: {}, curConversationId: "" };

export const useAgentStore = create<AgentStoreState>()(
  devtools(
    (set) => ({
      ...INITIAL,
      setCurConversationId: (curConversationId) =>
        set(() => ({ curConversationId })),
      resetStore: () => set(INITIAL),

      dispatchAgentStore: (action) =>
        set((s) => ({
          agentStore: updateAgentConversationsStore(s.agentStore, action),
        })),

      dispatchAgentStoreHistory: (
        conversationId,
        history,
        clearHistory = false,
      ) =>
        set((s) => ({
          agentStore: batchUpdateAgentConversationsStore(
            s.agentStore,
            conversationId,
            history,
            clearHistory,
          ),
        })),
    }),
    { name: "AgentStore", enabled: import.meta.env.DEV },
  ),
);

// Hooks with shallow comparison
export const useCurrentConversation = () =>
  useAgentStore(
    useShallow((s) => ({
      curConversation: s.agentStore[s.curConversationId] ?? null,
      curConversationId: s.curConversationId,
    })),
  );

export const useConversationById = (conversationId: string) =>
  useAgentStore(useShallow((s) => s.agentStore[conversationId] ?? null));

export const useAgentStoreActions = () =>
  useAgentStore(
    useShallow((s) => ({
      dispatchAgentStoreHistory: s.dispatchAgentStoreHistory,
      dispatchAgentStore: s.dispatchAgentStore,
      setCurConversationId: s.setCurConversationId,
      resetStore: s.resetStore,
    })),
  );
