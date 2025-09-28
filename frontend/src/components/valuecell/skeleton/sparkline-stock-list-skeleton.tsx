import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SparklineStockItemSkeletonProps
  extends React.HTMLAttributes<HTMLDivElement> {}

function SparklineStockItemSkeleton({
  className,
  ...props
}: SparklineStockItemSkeletonProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-md border border-[#eef0f3] p-3",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col items-start gap-1">
        {/* Stock symbol skeleton */}
        <div className="flex items-center gap-1">
          <Skeleton className="h-[20px] w-16" />
        </div>

        {/* Price skeleton */}
        <Skeleton className="h-[26px] w-20" />

        {/* Change amount and percentage skeleton */}
        <div className="flex items-start gap-1">
          <Skeleton className="h-[16px] w-12" />
          <Skeleton className="h-[16px] w-14" />
        </div>
      </div>

      {/* Sparkline chart skeleton */}
      <Skeleton className="pointer-events-none h-16 w-[140px] rounded-sm" />
    </div>
  );
}

interface SparklineStockListSkeletonProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Number of skeleton items to render
   * @default 6
   */
  count?: number;
}

function SparklineStockListSkeleton({
  className,
  count = 6,
  ...props
}: SparklineStockListSkeletonProps) {
  const skeletonItems = Array.from({ length: count }, (_, index) => ({
    id: `skeleton-stock-${Date.now()}-${index}`,
  }));

  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
        className,
      )}
      {...props}
    >
      {skeletonItems.map((item) => (
        <SparklineStockItemSkeleton key={item.id} />
      ))}
    </div>
  );
}

export { SparklineStockListSkeleton, SparklineStockItemSkeleton };
