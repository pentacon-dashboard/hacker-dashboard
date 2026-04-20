import { Skeleton } from "@/components/ui/skeleton";

interface LoadingSkeletonProps {
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({ rows = 3, className }: LoadingSkeletonProps) {
  return (
    <div className={className} aria-busy="true" aria-label="로딩 중">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="mb-2 h-10 w-full" />
      ))}
    </div>
  );
}

export function CardLoadingSkeleton() {
  return (
    <div
      className="rounded-lg border bg-card p-6"
      aria-busy="true"
      aria-label="로딩 중"
    >
      <Skeleton className="mb-4 h-4 w-1/3" />
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="mt-2 h-3 w-1/2" />
    </div>
  );
}
