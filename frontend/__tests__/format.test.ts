import { describe, expect, it } from "vitest";
import {
  formatConfidence,
  formatCost,
  formatDate,
  formatDuration,
  formatModelName,
  triageLevelColor,
} from "../src/utils/format";

describe("formatConfidence", () => {
  it("formats 0.82 as 82%", () => {
    expect(formatConfidence(0.82)).toBe("82%");
  });

  it("formats 1.0 as 100%", () => {
    expect(formatConfidence(1.0)).toBe("100%");
  });

  it("formats 0 as 0%", () => {
    expect(formatConfidence(0)).toBe("0%");
  });
});

describe("formatCost", () => {
  it("formats tiny costs with 5 decimal places", () => {
    expect(formatCost(0.00015)).toBe("$0.00015");
  });

  it("formats larger costs with 4 decimal places", () => {
    expect(formatCost(0.05)).toBe("$0.0500");
  });
});

describe("formatDuration", () => {
  it("formats sub-second as ms", () => {
    expect(formatDuration(200)).toBe("200ms");
  });

  it("formats seconds with decimal", () => {
    expect(formatDuration(1500)).toBe("1.5s");
  });
});

describe("formatDate", () => {
  it("formats ISO string to readable date", () => {
    const result = formatDate("2025-01-15T14:30:00Z");
    expect(result).toContain("Jan");
    expect(result).toContain("15");
  });
});

describe("formatModelName", () => {
  it("extracts Opus from model ID", () => {
    expect(formatModelName("claude-opus-4-6-20250929")).toBe("Opus");
  });

  it("extracts Sonnet from model ID", () => {
    expect(formatModelName("claude-sonnet-4-5-20250929")).toBe("Sonnet");
  });

  it("extracts Haiku from model ID", () => {
    expect(formatModelName("claude-haiku-4-5-20241022")).toBe("Haiku");
  });

  it("returns raw string for unknown model", () => {
    expect(formatModelName("gpt-4")).toBe("gpt-4");
  });
});

describe("triageLevelColor", () => {
  it("returns red classes for Emergency", () => {
    expect(triageLevelColor("Emergency")).toContain("red");
  });

  it("returns orange classes for Urgent", () => {
    expect(triageLevelColor("Urgent")).toContain("orange");
  });

  it("returns yellow classes for Semi-Urgent", () => {
    expect(triageLevelColor("Semi-Urgent")).toContain("yellow");
  });

  it("returns green classes for Non-Urgent", () => {
    expect(triageLevelColor("Non-Urgent")).toContain("green");
  });

  it("returns gray for unknown level", () => {
    expect(triageLevelColor("Unknown")).toContain("gray");
  });
});
