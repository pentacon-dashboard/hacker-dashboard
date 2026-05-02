import { Suspense } from "react";
import { ClientDashboardHome } from "@/components/clients/client-dashboard-home";
import { Skeleton } from "@/components/ui/skeleton";

export default function HomePage() {
  return (
    <Suspense fallback={<HomePageSkeleton />}>
      <ClientDashboardHome />
    </Suspense>
  );
}

function HomePageSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-8 w-40" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <div className="grid gap-3 xl:grid-cols-[285px_minmax(0,1fr)]">
        <Skeleton className="h-[520px] w-full" />
        <Skeleton className="h-[520px] w-full" />
      </div>
    </div>
  );
}
