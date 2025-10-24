import { Settings } from "lucide-react";
import { type FC, memo } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import AgentAvatar from "@/components/valuecell/agent-avatar";
import AppConversationSheet from "@/components/valuecell/app-conversation-sheet";
import type { AgentInfo } from "@/types/agent";

interface ChatConversationHeaderProps {
  agent: AgentInfo;
}

const ChatConversationHeader: FC<ChatConversationHeaderProps> = ({ agent }) => {
  return (
    <header className="flex w-full items-center justify-between p-6">
      <div className="flex items-center gap-2">
        <AppConversationSheet />

        {/* Agent Avatar */}
        <AgentAvatar agentName={agent.agent_name} className="size-14" />

        {/* Agent Info */}
        <div className="flex flex-col gap-1.5">
          <h1 className="font-semibold text-gray-950 text-lg">
            {agent.display_name}
          </h1>
          <div className="flex items-center gap-1">
            {agent.agent_metadata.tags.map((tag) => (
              <span
                key={tag}
                className="text-nowrap rounded-md bg-gray-100 px-3 py-1 font-normal text-gray-700 text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2.5">
        {/* TODO: add new conversation button */}
        {/* <Button
          variant="secondary"
          className="size-8 cursor-pointer rounded-lg"
          size="icon"
        >
          <MessageCircle size={16} className="text-gray-700" />
        </Button> */}
        <Link to="./config">
          <Button
            variant="secondary"
            className="size-8 cursor-pointer rounded-lg hover:bg-gray-200"
            size="icon"
          >
            <Settings size={16} className="text-gray-700" />
          </Button>
        </Link>
      </div>
    </header>
  );
};

export default memo(ChatConversationHeader);
