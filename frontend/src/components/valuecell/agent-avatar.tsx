import type { FC } from "react";
import { AGENT_AVATAR_MAP } from "@/constants/agent";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";

export interface AgentAvatarProps {
  className?: string;
  agentName: string;
}

export const AgentAvatar: FC<AgentAvatarProps> = ({ agentName, className }) => {
  return (
    <Avatar className={cn("size-full", className)}>
      <AvatarImage src={AGENT_AVATAR_MAP[agentName]} />
      <AvatarFallback>{agentName.slice(0, 2)}</AvatarFallback>
    </Avatar>
  );
};

export default AgentAvatar;
