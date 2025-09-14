import { cn } from "@/lib/utils";

interface AgentMenuProps extends React.HTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  onClick?: () => void;
}

interface AgentMenuContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface AgentMenuSuffixProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface AgentMenuIconProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface AgentMenuTitleProps
  extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

function AgentMenu({ className, children, onClick, ...props }: AgentMenuProps) {
  return (
    <button
      className={cn(
        "border border-white bg-white backdrop-blur-[2px] backdrop-filter",
        "relative flex items-center justify-between rounded-xl px-4 py-3 transition-colors",
        onClick && "cursor-pointer hover:bg-gray-50",
        className,
      )}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}

function AgentMenuContent({
  className,
  children,
  ...props
}: AgentMenuContentProps) {
  return (
    <div
      className={cn("flex shrink-0 items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}

function AgentMenuSuffix({
  className,
  children,
  ...props
}: AgentMenuSuffixProps) {
  return (
    <div className={cn("flex shrink-0 items-center", className)} {...props}>
      {children}
    </div>
  );
}

function AgentMenuIcon({ className, children, ...props }: AgentMenuIconProps) {
  return (
    <div
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#eef0f3] p-2",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function AgentMenuTitle({
  className,
  children,
  ...props
}: AgentMenuTitleProps) {
  return (
    <p
      className={cn(
        "whitespace-nowrap font-normal text-black text-sm leading-[22px]",
        className,
      )}
      title={typeof children === "string" ? children : undefined}
      {...props}
    >
      {children}
    </p>
  );
}

export {
  AgentMenu,
  AgentMenuContent,
  AgentMenuSuffix,
  AgentMenuIcon,
  AgentMenuTitle,
};
