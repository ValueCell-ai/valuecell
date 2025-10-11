import {
  AgentMenuCard,
  AgentMenuContent,
  AgentMenuDescription,
  AgentMenuIcon,
  AgentMenuSuffix,
  AgentMenuTitle,
} from "@/components/valuecell/menus/agent-menus";
import { cn } from "@/lib/utils";

export interface AgentSuggestion {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  avatars?: React.ReactNode[];
  bgColor?: string; // Tailwind CSS background color class
  decorativeGraphics?: React.ReactNode;
  onClick?: () => void;
}

interface AgentSuggestionsListProps
  extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actionText?: string;
  suggestions: AgentSuggestion[];
  onActionClick?: () => void;
}

interface AgentSuggestionsHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  actionText?: string;
  onActionClick?: () => void;
}

interface AgentSuggestionItemProps
  extends Omit<React.HTMLAttributes<HTMLButtonElement>, "onClick"> {
  suggestion: AgentSuggestion;
}

function AgentSuggestionsHeader({
  className,
  title,
  actionText,
  onActionClick,
  ...props
}: AgentSuggestionsHeaderProps) {
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

function AgentSuggestionItem({
  className,
  suggestion,
  ...props
}: AgentSuggestionItemProps) {
  return (
    <AgentMenuCard
      className={cn("h-[140px] cursor-pointer", className)}
      onClick={suggestion.onClick}
      bgColor={suggestion.bgColor}
      {...props}
    >
      {/* Left content area */}
      <div className="relative z-10 flex h-full flex-col justify-between">
        <AgentMenuContent className="flex-col items-start gap-2">
          {/* Icon and title row */}
          <div className="flex items-center gap-2">
            <AgentMenuIcon className="size-6 p-1.5">
              {suggestion.icon}
            </AgentMenuIcon>
            <AgentMenuTitle className="font-medium text-base text-gray-950 leading-5.5">
              {suggestion.title}
            </AgentMenuTitle>
          </div>

          {/* Description text */}
          <AgentMenuDescription>{suggestion.description}</AgentMenuDescription>
        </AgentMenuContent>

        {/* Bottom user avatars */}
        {suggestion.avatars && suggestion.avatars.length > 0 && (
          <AgentMenuSuffix>
            <div className="flex items-center">
              {suggestion.avatars.map((avatar, index) => (
                <div
                  key={`${suggestion.id}-avatar-${index}`}
                  className="-mr-2 relative size-6 overflow-hidden rounded-full border-2 border-white last:mr-0"
                >
                  {avatar}
                </div>
              ))}
            </div>
          </AgentMenuSuffix>
        )}
      </div>

      {/* Right decorative graphics area */}
      <div className="absolute right-4 bottom-0 h-[110px] w-[140px]">
        {suggestion.decorativeGraphics}
      </div>
    </AgentMenuCard>
  );
}

function AgentSuggestionsList({
  className,
  title,
  actionText,
  suggestions,
  onActionClick,
  ...props
}: AgentSuggestionsListProps) {
  return (
    <div className={cn("flex flex-col gap-4", className)} {...props}>
      {(title || actionText) && (
        <AgentSuggestionsHeader
          title={title}
          actionText={actionText}
          onActionClick={onActionClick}
        />
      )}

      <div className="flex w-full gap-4 pb-2">
        {suggestions.map((suggestion) => (
          <AgentSuggestionItem key={suggestion.id} suggestion={suggestion} />
        ))}
      </div>
    </div>
  );
}

export { AgentSuggestionsList, AgentSuggestionsHeader, AgentSuggestionItem };
