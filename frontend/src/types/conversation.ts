import type { SSEData } from "./agent";

export type ConversationItem = {
  conversation_id: string;
  title: string;
  agent_name: string;
  update_time: string;
};

export type ConversationList = {
  conversations: ConversationItem[];
  total: number;
};

export type ConversationHistory = {
  conversation_id: string;
  items: SSEData[];
};
