export function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

export function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(5)}`;
  return `$${usd.toFixed(4)}`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatModelName(model: string): string {
  if (model.includes("opus")) return "Opus";
  if (model.includes("sonnet")) return "Sonnet";
  if (model.includes("haiku")) return "Haiku";
  return model;
}

export function triageLevelColor(level: string): string {
  switch (level) {
    case "Emergency":
      return "text-red-700 bg-red-50 border-red-200";
    case "Urgent":
      return "text-orange-700 bg-orange-50 border-orange-200";
    case "Semi-Urgent":
      return "text-yellow-700 bg-yellow-50 border-yellow-200";
    case "Non-Urgent":
      return "text-green-700 bg-green-50 border-green-200";
    default:
      return "text-gray-700 bg-gray-50 border-gray-200";
  }
}
