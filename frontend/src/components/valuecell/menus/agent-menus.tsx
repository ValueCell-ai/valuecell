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

interface AgentMenuDescriptionProps
  extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

interface AgentMenuCardProps extends React.HTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  onClick?: () => void;
  bgColor?: string; // Tailwind CSS background color class
}

function AgentMenu({ className, children, onClick, ...props }: AgentMenuProps) {
  return (
    <button
      className={cn(
        "border border-border bg-card backdrop-blur-[2px] backdrop-filter",
        "relative flex items-center justify-between rounded-xl px-4 py-3 transition-colors",
        onClick && "cursor-pointer hover:bg-muted",
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
        "flex size-6 shrink-0 items-center justify-center rounded-[6px] bg-muted p-1",
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
        "whitespace-nowrap font-medium text-[16px] text-foreground leading-[22px]",
        className,
      )}
      title={typeof children === "string" ? children : undefined}
      {...props}
    >
      {children}
    </p>
  );
}

function AgentMenuDescription({
  className,
  children,
  ...props
}: AgentMenuDescriptionProps) {
  return (
    <p
      className={cn(
        "line-clamp-2 text-left text-muted-foreground text-sm leading-4.5",
        className,
      )}
      {...props}
    >
      {children}
    </p>
  );
}

function AgentMenuCard({
  className,
  children,
  onClick,
  bgColor,
  ...props
}: AgentMenuCardProps) {
  return (
    <button
      type="button"
      className={cn(
        "relative flex-1 overflow-hidden rounded-xl border border-border p-4 transition-all hover:shadow-md",
        bgColor || "bg-card",
        className,
      )}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}

export {
  AgentMenu,
  AgentMenuContent,
  AgentMenuSuffix,
  AgentMenuIcon,
  AgentMenuTitle,
  AgentMenuDescription,
  AgentMenuCard,
};
