import { type FC, memo } from "react";
import { NavLink } from "react-router";
import { AgentAvatar } from "@/components/valuecell/icon/agent-avatar";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import { TimeUtils } from "@/lib/time";
import type { TaskCardItem } from "@/types/conversation";

const AgentTaskCard: FC<TaskCardItem> = ({
  agent_name,
  update_time,
  results,
}) => {
  if (results.length === 0) return null;

  const Component =
    COMPONENT_RENDERER_MAP[results[0].data.payload?.component_type];
  if (!Component) return null;

  return (
    <div className="flex size-full flex-col gap-4 rounded-lg border border-gray-100 bg-[linear-gradient(98deg,#FFF_5.05%,#E7EFFF_100%)] px-5 py-4">
      <div className="flex w-full items-center justify-between">
        <div className="flex shrink-0 items-center gap-2">
          <AgentAvatar agentName={agent_name} className="size-8" />
          <p className="whitespace-nowrap font-normal text-base text-gray-950 leading-[22px]">
            {agent_name}
          </p>
        </div>
        <p className="shrink-0 whitespace-nowrap text-gray-400 text-xs leading-[18px]">
          {TimeUtils.fromUTCRelative(update_time)}
        </p>
      </div>

      <div className="flex w-full flex-col gap-2">
        {[...results]
          .reverse()
          .slice(0, 3)
          .map((result) => (
            <NavLink
              key={result.data.item_id}
              to={`/agent/${agent_name}?id=${result.data.conversation_id}`}
            >
              <Component content={result.data.payload.content} />
            </NavLink>
          ))}
      </div>
    </div>
  );
};

const AgentTaskCards: FC<{ tasks: TaskCardItem[] }> = ({ tasks }) => {
  return (
    <div className="columns-2 gap-4">
      {tasks.map((task) => (
        <section key={task.agent_name} className="mb-3 break-inside-avoid">
          <AgentTaskCard {...task} />
        </section>
      ))}
    </div>
  );
};

export default memo(AgentTaskCards);
