import type { FC } from "react";
import { AgentAvatar } from "@/components/valuecell/icon/agent-avatar";
import { cn } from "@/lib/utils";
import type { AgentInfo } from "@/types/agent";

export interface AgentCardProps extends React.HTMLAttributes<HTMLDivElement> {
  agent: AgentInfo;
}

export const AgentCard: FC<AgentCardProps> = ({
  agent,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        "box-border flex w-full cursor-pointer flex-col gap-5 p-6",
        "rounded-2xl border border-gray-200 bg-white shadow-sm",
        "transition-all duration-300",
        "hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md",
        className,
      )}
      {...props}
    >
      {/* Avatar and Name Section */}
      <div className="flex w-full items-center gap-3">
        {/* Avatar */}
        <div className="size-12 shrink-0">
          <AgentAvatar agentName={agent.agent_name} />
        </div>

        {/* Name */}
        <h3 className="line-clamp-1 font-semibold text-gray-900 text-lg leading-6">
          {agent.display_name}
        </h3>
      </div>

      {/* Description */}
      <p className="line-clamp-3 w-full text-gray-600 text-sm leading-6">
        {agent.description}
      </p>
    </div>
  );
};

export default AgentCard;
