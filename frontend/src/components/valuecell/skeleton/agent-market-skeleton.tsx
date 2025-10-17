import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface AgentCardSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

function AgentCardSkeleton({ className, ...props }: AgentCardSkeletonProps) {
  return (
    <div
      className={cn(
        "box-border flex w-full flex-col items-center gap-4 rounded-xl border border-gray-100 bg-neutral-50 p-4",
        className,
      )}
      {...props}
    >
      {/* Avatar and Name Section */}
      <div className="flex w-full flex-col items-start gap-2">
        <div className="flex w-full items-center gap-2">
          {/* Avatar skeleton */}
          <div className="flex shrink-0 items-center gap-2.5">
            <Skeleton className="size-8 rounded-full" />
          </div>

          {/* Name skeleton */}
          <Skeleton className="h-[22px] w-32" />
        </div>
      </div>

      {/* Description skeleton */}
      <div className="flex w-full flex-col gap-2">
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-3/4" />
      </div>
    </div>
  );
}

interface AgentMarketSkeletonProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Number of skeleton cards to render
   * @default 12
   */
  count?: number;
}

function AgentMarketSkeleton({
  className,
  count = 12,
  ...props
}: AgentMarketSkeletonProps) {
  const skeletonItems = Array.from({ length: count }, (_, index) => ({
    id: `skeleton-agent-${Date.now()}-${index}`,
  }));

  return (
    <div
      className={cn(
        "flex size-full flex-col items-center justify-start gap-8 py-8",
        className,
      )}
      {...props}
    >
      {/* Page Title skeleton */}
      <Skeleton className="h-7 w-48" />

      {/* Agent Cards Grid */}
      <div className="columns-3 gap-4 space-y-4">
        {skeletonItems.map((item) => (
          <div key={item.id} className="break-inside-avoid">
            <AgentCardSkeleton />
          </div>
        ))}
      </div>
    </div>
  );
}

export { AgentMarketSkeleton, AgentCardSkeleton };
