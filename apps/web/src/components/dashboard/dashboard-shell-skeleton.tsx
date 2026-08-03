import { PageSkeleton } from "@/components/page-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardShellSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading dashboard"
      className="min-h-svh bg-background"
      role="status"
    >
      <div className="hidden border-r bg-sidebar p-4 md:fixed md:inset-y-0 md:block md:w-64">
        <Skeleton className="h-10 w-full" />
        <div className="mt-8 space-y-3">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton className="h-8 w-full" key={index} />
          ))}
        </div>
      </div>
      <main className="md:pl-64">
        <div className="border-b px-4 py-4 md:px-6">
          <Skeleton className="h-7 w-56" />
        </div>
        <div className="mx-auto max-w-screen-2xl p-4 md:p-6">
          <PageSkeleton />
        </div>
      </main>
    </div>
  );
}
