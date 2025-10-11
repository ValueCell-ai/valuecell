import {
  AgentMenu,
  AgentMenuContent,
  AgentMenuIcon,
  AgentMenuTitle,
} from "@valuecell/menus/agent-menus";
import { Link } from "react-router";
import { Marquee } from "@/components/magicui/marquee";
import { cn } from "@/lib/utils";

export interface AgentRecommendation {
  id: string;
  title: string;
  icon: React.ReactNode;
  onClick?: () => void;
}

interface AgentRecommendListProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actionText?: string;
  recommendations: AgentRecommendation[];
  onActionClick?: () => void;
  /**
   * Whether to pause scrolling on hover
   * @default true
   */
  pauseOnHover?: boolean;
  /**
   * Animation duration for the marquee
   * @default "40s"
   */
  duration?: string;
  /**
   * Gap between items in the marquee
   * @default "0.75rem"
   */
  gap?: string;
}

interface AgentRecommendHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actionText?: string;
  onActionClick?: () => void;
}

interface AgentRecommendItemProps
  extends Omit<React.HTMLAttributes<HTMLButtonElement>, "onClick"> {
  recommendation: AgentRecommendation;
}

function AgentRecommendHeader({
  className,
  title,
  actionText,
  onActionClick,
  ...props
}: AgentRecommendHeaderProps) {
  return (
    <div
      className={cn("flex items-center justify-between", className)}
      {...props}
    >
      {title && (
        <h2 className="font-medium text-black text-xl leading-7">{title}</h2>
      )}
      {actionText && (
        <button
          type="button"
          onClick={onActionClick}
          className="font-normal text-base text-black/60 transition-colors hover:text-black/80"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}

function AgentRecommendItem({
  className,
  recommendation,
  ...props
}: AgentRecommendItemProps) {
  return (
    <Link to={`/agent/${recommendation.id}`}>
      <AgentMenu
        className={cn(
          "cursor-pointer gap-2 rounded-xl border-none bg-gray-100 px-4 py-3 transition-colors hover:bg-gray-200",
          className,
        )}
        onClick={recommendation.onClick}
        {...props}
      >
        <AgentMenuContent className="gap-2">
          <AgentMenuIcon className="size-8 bg-transparent p-0">
            {recommendation.icon}
          </AgentMenuIcon>
          <AgentMenuTitle className="whitespace-nowrap text-sm leading-6">
            {recommendation.title}
          </AgentMenuTitle>
        </AgentMenuContent>
      </AgentMenu>
    </Link>
  );
}

function AgentRecommendList({
  className,
  title,
  actionText,
  recommendations,
  onActionClick,
  pauseOnHover = true,
  duration = "30s",
  gap = "0.75rem",
  ...props
}: AgentRecommendListProps) {
  // Split recommendations into two rows for better visual balance
  const midPoint = Math.ceil(recommendations.length / 2);
  const firstRow = recommendations.slice(0, midPoint);
  const secondRow = recommendations.slice(midPoint);

  const marqueeStyle = {
    "--duration": duration,
    "--gap": gap,
  } as React.CSSProperties;

  return (
    <div className={cn("flex flex-col gap-4", className)} {...props}>
      {(title || actionText) && (
        <AgentRecommendHeader
          title={title}
          actionText={actionText}
          onActionClick={onActionClick}
        />
      )}

      <div
        className="flex w-full max-w-full flex-col gap-2.5"
        style={marqueeStyle}
      >
        {/* First row - normal direction */}
        <div className="w-full overflow-hidden">
          <Marquee
            className="p-0 [gap:var(--gap)]"
            pauseOnHover={pauseOnHover}
            reverse={false}
          >
            {firstRow.map((recommendation) => (
              <AgentRecommendItem
                key={`first-${recommendation.id}`}
                recommendation={recommendation}
              />
            ))}
          </Marquee>
        </div>

        {/* Second row - reverse direction for visual variety */}
        <div className="w-full overflow-hidden">
          <Marquee
            className="p-0 [gap:var(--gap)]"
            pauseOnHover={pauseOnHover}
            reverse={true}
          >
            {secondRow.map((recommendation) => (
              <AgentRecommendItem
                key={`second-${recommendation.id}`}
                recommendation={recommendation}
              />
            ))}
          </Marquee>
        </div>
      </div>
    </div>
  );
}

export { AgentRecommendList, AgentRecommendHeader, AgentRecommendItem };
