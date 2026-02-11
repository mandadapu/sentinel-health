import { AnalyticsCards } from "@/components/AnalyticsCards";
import { ApprovalQueue } from "@/components/ApprovalQueue";
import { useTriageSessions } from "@/hooks/useTriageSessions";

export function DashboardPage() {
  const { sessions, loading, error } = useTriageSessions();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Failed to load sessions: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <AnalyticsCards sessions={sessions} />
      <div>
        <h2 className="mb-3 text-lg font-semibold">Approval Queue</h2>
        <ApprovalQueue sessions={sessions} />
      </div>
    </div>
  );
}
