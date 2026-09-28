type Schedule = { start_date: string; end_date: string };
export type GanttMonth = { key: string; label: string; days: number; left: number; width: number };
export type GanttRange = { start: number; end: number; months: GanttMonth[]; label: string };

const DAY = 24 * 60 * 60 * 1000;
const shortMonth = new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
const longMonth = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });

function parseDay(value: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000-')) return null;
  const timestamp = Date.parse(`${value}T00:00:00.000Z`);
  // Date.parse can normalize invalid dates such as February 30 into March.
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? timestamp : null;
}

function interval(schedule: Schedule): { start: number; end: number } | null {
  const start = parseDay(schedule.start_date), lastDay = parseDay(schedule.end_date);
  if (start === null || lastDay === null || lastDay < start) return null;
  // Scheduling dates include the final day, including a one-day project.
  return { start, end: lastDay + DAY };
}

function monthStart(timestamp: number, offset = 0): number {
  const date = new Date(timestamp);
  date.setUTCDate(1);
  date.setUTCMonth(date.getUTCMonth() + offset);
  return date.getTime();
}

export function buildGanttRange(schedules: readonly Schedule[]): GanttRange | null {
  let first = Infinity, last = -Infinity;
  for (const schedule of schedules) {
    const dates = interval(schedule);
    if (dates) {
      first = Math.min(first, dates.start);
      last = Math.max(last, dates.end - DAY);
    }
  }
  if (!Number.isFinite(first)) return null;
  const start = monthStart(first), end = monthStart(last, 1), duration = end - start;
  const months: GanttMonth[] = [];
  for (let cursor = start; cursor < end;) {
    const next = monthStart(cursor, 1);
    months.push({
      key: new Date(cursor).toISOString().slice(0, 7),
      label: shortMonth.format(cursor),
      days: (next - cursor) / DAY,
      left: (cursor - start) / duration * 100,
      width: (next - cursor) / duration * 100,
    });
    cursor = next;
  }
  const firstLabel = longMonth.format(start), lastLabel = longMonth.format(last);
  return { start, end, months, label: firstLabel === lastLabel ? firstLabel : `${firstLabel} — ${lastLabel}` };
}

export function ganttBarFor(schedule: Schedule, range: GanttRange): { left: number; width: number } | null {
  const dates = interval(schedule);
  if (!dates || range.end <= range.start) return null;
  const start = Math.max(range.start, dates.start), end = Math.min(range.end, dates.end);
  if (start >= end) return null;
  const duration = range.end - range.start;
  return { left: (start - range.start) / duration * 100, width: (end - start) / duration * 100 };
}
