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
