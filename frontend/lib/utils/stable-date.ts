export const APP_TIME_ZONE = "Asia/Seoul";

function getDateParts(date: Date, timeZone = APP_TIME_ZONE) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);

  const values = new Map(parts.map((part) => [part.type, part.value]));
  const year = values.get("year");
  const month = values.get("month");
  const day = values.get("day");

  if (!year || !month || !day) {
    throw new Error("Unable to format calendar date");
  }

  return { year, month, day };
}

export function getDateKeyInTimeZone(
  date: Date = new Date(),
  timeZone = APP_TIME_ZONE,
): string {
  const { year, month, day } = getDateParts(date, timeZone);
  return `${year}-${month}-${day}`;
}

export function getYearInTimeZone(
  date: Date = new Date(),
  timeZone = APP_TIME_ZONE,
): number {
  return Number(getDateParts(date, timeZone).year);
}

export function addDaysToDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split("-").map(Number);
  if (!year || !month || !day) {
    throw new Error(`Invalid date key: ${dateKey}`);
  }

  const date = new Date(Date.UTC(year, month - 1, day + days));
  return date.toISOString().slice(0, 10);
}

export function dateKeyToDate(dateKey: string): Date {
  return new Date(`${dateKey}T00:00:00.000Z`);
}

export function formatDateInAppTimeZone(
  date: Date,
  localeTag: string,
  options: Intl.DateTimeFormatOptions,
): string {
  return new Intl.DateTimeFormat(localeTag, {
    ...options,
    timeZone: APP_TIME_ZONE,
  }).format(date);
}
