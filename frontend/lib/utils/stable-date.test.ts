import { describe, expect, it } from "vitest";
import {
  addDaysToDateKey,
  formatDateInAppTimeZone,
  getDateKeyInTimeZone,
} from "./stable-date";

describe("stable-date", () => {
  it("uses the app time zone for server/client stable calendar dates", () => {
    const utcEvening = new Date("2026-05-12T20:00:00.000Z");

    expect(getDateKeyInTimeZone(utcEvening)).toBe("2026-05-13");
    expect(addDaysToDateKey("2026-05-13", -30)).toBe("2026-04-13");
  });

  it("formats timestamps in the same app time zone during SSR and hydration", () => {
    const formatted = formatDateInAppTimeZone(
      new Date("2026-05-12T20:52:00.000Z"),
      "ko-KR",
      {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      },
    );

    expect(formatted).toContain("5월 13일");
  });
});
