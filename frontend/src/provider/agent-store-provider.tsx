import {
  createContext,
  type Dispatch,
  type FC,
  type ReactNode,
  type RefObject,
  use,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import type {
  AgentConversationsStore,
  ConversationView,
  SSEData,
} from "@/types/agent";

// Optimized reducer for agent store management
function agentStoreReducer(
  state: AgentConversationsStore,
  action: SSEData,
): AgentConversationsStore {
  return updateAgentConversationsStore(state, action);
}

interface AgentStoreContextType {
  agentStore: AgentConversationsStore;
  dispatchAgentStore: Dispatch<SSEData>;
  curConversationId: string;
  setCurConversationId: (conversationId: string) => void;
  currentConversation: ConversationView | null;
  curThreadId: RefObject<string>;
}

const AgentStoreContext = createContext<AgentStoreContextType | null>(null);

interface AgentStoreProviderProps {
  children: ReactNode;
  agentName: string;
}

export const AgentStoreProvider: FC<AgentStoreProviderProps> = ({
  children,
  agentName,
}) => {
  // Use optimized reducer for state management
  const [agentStore, dispatchAgentStore] = useReducer(agentStoreReducer, {});

  // TODO: temporary conversation id (after will remove hardcoded)
  const [curConversationId, setCurConversationId] = useState<string>(
    `${agentName}_conv_default_user`,
  );
  const curThreadId = useRef<string>("");

  // Only update conversation ID when agentName actually changes
  useEffect(() => {
    const newConversationId = `${agentName}_conv_default_user`;
    if (curConversationId !== newConversationId) {
      setCurConversationId(newConversationId);
    }
  }, [agentName, curConversationId]);

  // Get current conversation using original data structure
  const currentConversation = useMemo(() => {
    return curConversationId in agentStore
      ? agentStore[curConversationId]
      : null;
  }, [agentStore, curConversationId]);

  const contextValue: AgentStoreContextType = useMemo(
    () => ({
      agentStore,
      dispatchAgentStore,
      curConversationId,
      setCurConversationId,
      currentConversation,
      curThreadId,
    }),
    [agentStore, curConversationId, currentConversation],
  );

  return (
    <AgentStoreContext.Provider value={contextValue}>
      {children}
    </AgentStoreContext.Provider>
  );
};

export const useAgentStore = (): AgentStoreContextType => {
  const context = use(AgentStoreContext);
  if (!context) {
    throw new Error("useAgentStore must be used within an AgentStoreProvider");
  }
  return context;
};
