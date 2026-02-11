import { formatConfidence } from "@/utils/format";

function colorForConfidence(value: number): string {
  if (value >= 0.85) return "bg-green-100 text-green-800";
  if (value >= 0.70) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function ConfidenceBadge({ value }: { value: number }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorForConfidence(value)}`}
    >
      {formatConfidence(value)}
    </span>
  );
}
