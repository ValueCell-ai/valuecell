import { MessageCircle, Settings } from "lucide-react";
import { type FC, memo } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import TagGroups from "@/components/valuecell/button/tag-groups";
import AgentAvatar from "@/components/valuecell/icon/agent-avatar";
import type { AgentInfo } from "@/types/agent";

interface ChatConversationHeaderProps {
  agent: AgentInfo;
}

const ChatConversationHeader: FC<ChatConversationHeaderProps> = ({ agent }) => {
  return (
    <header className="flex w-full items-center justify-between p-6">
      <div className="flex items-center gap-2">
        {/* Agent Avatar */}
        <AgentAvatar agentName={agent.agent_name} className="size-14" />

        {/* Agent Info */}
        <div className="flex flex-col gap-1.5">
          <h1 className="font-semibold text-gray-950 text-lg">
            {agent.display_name}
          </h1>
          <TagGroups tags={agent.agent_metadata.tags} />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2.5">
        <Link to=".">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="secondary"
                className="size-8 cursor-pointer rounded-lg hover:bg-gray-200"
                size="icon"
              >
                <MessageCircle size={16} className="text-gray-700" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>New Conversation</TooltipContent>
          </Tooltip>
        </Link>
        <Link to="./config">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="secondary"
                className="size-8 cursor-pointer rounded-lg hover:bg-gray-200"
                size="icon"
              >
                <Settings size={16} className="text-gray-700" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Settings</TooltipContent>
          </Tooltip>
        </Link>
      </div>
    </header>
  );
};

export default memo(ChatConversationHeader);
