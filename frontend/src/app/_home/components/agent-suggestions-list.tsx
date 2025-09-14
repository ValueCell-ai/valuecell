import {
  AgentMenu,
  AgentMenuContent,
  AgentMenuIcon,
  AgentMenuSuffix,
  AgentMenuTitle,
} from "@valuecell/menus/agent-menus";
import { cn } from "@/lib/utils";

export interface AgentSuggestion {
  id: string;
  title: string;
  icon: React.ReactNode;
  avatars?: React.ReactNode[];
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
    <AgentMenu
      className={cn("flex-1", className)}
      onClick={suggestion.onClick}
      {...props}
    >
      <AgentMenuContent className="flex-1 overflow-hidden">
        <AgentMenuIcon>{suggestion.icon}</AgentMenuIcon>
        <AgentMenuTitle className="overflow-hidden text-ellipsis">
          {suggestion.title}
        </AgentMenuTitle>
      </AgentMenuContent>

      {suggestion.avatars && suggestion.avatars.length > 0 && (
        <AgentMenuSuffix>
          <div className="flex items-center">
            {suggestion.avatars.map((avatar, index) => (
              <div
                key={`${suggestion.id}-avatar-${index}`}
                className="-mr-2 relative size-6 overflow-hidden rounded-full border border-white last:mr-0"
              >
                {avatar}
              </div>
            ))}
          </div>
        </AgentMenuSuffix>
      )}
    </AgentMenu>
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

      <div
        className={cn(
          "grid gap-3 rounded-2xl p-6",
          "bg-gradient-to-r from-[#CFE2FF]/50 to-[#FADDFF]/50",
          "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
        )}
      >
        {suggestions.map((suggestion) => (
          <AgentSuggestionItem key={suggestion.id} suggestion={suggestion} />
        ))}
      </div>
    </div>
  );
}

export { AgentSuggestionsList, AgentSuggestionsHeader, AgentSuggestionItem };
