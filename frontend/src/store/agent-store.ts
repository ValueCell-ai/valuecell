import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/shallow";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import type { AgentConversationsStore, SSEData } from "@/types/agent";

interface AgentStoreState {
  agentStore: AgentConversationsStore;
  curConversationId: string;
  dispatchAgentStore: (action: SSEData) => void;
  setCurConversationId: (conversationId: string) => void;
  resetStore: () => void;
}

const INITIAL = { agentStore: {}, curConversationId: "" };

export const useAgentStore = create<AgentStoreState>()(
  devtools(
    (set) => ({
      ...INITIAL,
      setCurConversationId: (curConversationId) => set({ curConversationId }),
      resetStore: () => set(INITIAL),

      dispatchAgentStore: (action) =>
        set((s) => ({
          agentStore: updateAgentConversationsStore(s.agentStore, action),
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
      dispatchAgentStore: s.dispatchAgentStore,
      setCurConversationId: s.setCurConversationId,
      resetStore: s.resetStore,
    })),
  );
