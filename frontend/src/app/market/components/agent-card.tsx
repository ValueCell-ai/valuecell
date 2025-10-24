import type { FC } from "react";
import { AgentAvatar } from "@/components/valuecell/agent-avatar";
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
        "box-border flex w-full cursor-pointer flex-col items-center gap-4 p-4",
        "rounded-xl border border-gray-100 bg-neutral-50",
        "transition-all duration-200",
        "hover:border-gray-200 hover:bg-neutral-100 hover:shadow-sm",
        className,
      )}
      {...props}
    >
      {/* Avatar and Name Section */}
      <div className="flex w-full flex-col items-start gap-2">
        <div className="flex w-full items-center gap-2">
          {/* Avatar */}
          <div className="flex shrink-0 items-center gap-2.5">
            <div className="size-8 shrink-0">
              <AgentAvatar agentName={agent.agent_name} />
            </div>
          </div>

          {/* Name */}
          <p className="shrink-0 whitespace-nowrap font-semibold text-base text-gray-950 leading-[22px]">
            {agent.display_name}
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="line-clamp-3 w-full font-normal text-gray-600 text-sm leading-5">
        {agent.description}
      </p>
    </div>
  );
};

export default AgentCard;
