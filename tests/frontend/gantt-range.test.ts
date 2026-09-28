import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildGanttRange, ganttBarFor } from '../../apps/web/lib/gantt-range';

const day = 24 * 60 * 60 * 1000;
const schedule = (start_date: string, end_date = start_date) => ({ start_date, end_date });
const iso = (timestamp: number) => new Date(timestamp).toISOString().slice(0, 10);
const close = (actual: number, expected: number) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);

test('empty or entirely invalid schedules have no fabricated horizon', () => {
  assert.equal(buildGanttRange([]), null);
  assert.equal(buildGanttRange([schedule('invalid', '2030-01-01')]), null);
  assert.equal(buildGanttRange([schedule('2030-03-01', '2030-02-01')]), null);
  assert.equal(buildGanttRange([schedule('2027-02-29')]), null);
});

test('past and future projects both set the calendar-month horizon', () => {
  const range = buildGanttRange([schedule('2031-03-17', '2031-05-02'), schedule('2024-11-20', '2024-12-04')])!;
  assert.equal(iso(range.start), '2024-11-01');
  assert.equal(iso(range.end), '2031-06-01');
  assert.equal(range.months[0].label, 'Nov 2024');
  assert.equal(range.months.at(-1)!.label, 'May 2031');
  assert.equal(range.label, 'November 2024 — May 2031');
});

test('month ticks use real month lengths across a leap year', () => {
  const range = buildGanttRange([schedule('2024-01-10', '2024-03-03')])!;
  assert.deepEqual(range.months.map(month => month.days), [31, 29, 31]);
  close(range.months[1].left, 31 / 91 * 100);
  close(range.months[2].left, 60 / 91 * 100);
  close(range.months.reduce((total, month) => total + month.width, 0), 100);
  assert.equal(range.end - range.start, 91 * day);
});

test('a one-day project has exactly one inclusive day of visible width', () => {
  const project = schedule('2032-02-29');
  const range = buildGanttRange([project])!;
  const bar = ganttBarFor(project, range)!;
  assert.equal(range.label, 'February 2032');
  assert.equal(range.months.length, 1);
  close(bar.left, 28 / 29 * 100);
  close(bar.width, 1 / 29 * 100);
  close(bar.left + bar.width, 100);
});

test('December to January ticks carry their actual years and inclusive end', () => {
  const project = schedule('2029-12-01', '2030-01-31');
  const range = buildGanttRange([project])!;
  assert.deepEqual(range.months.map(month => month.key), ['2029-12', '2030-01']);
  assert.deepEqual(range.months.map(month => month.label), ['Dec 2029', 'Jan 2030']);
  assert.deepEqual(ganttBarFor(project, range), { left: 0, width: 100 });
});

test('DST changes do not distort calendar-day positions', () => {
  const range = buildGanttRange([schedule('2026-03-01', '2026-03-31')])!;
  const bar = ganttBarFor(schedule('2026-03-07', '2026-03-09'), range)!;
  close(bar.left, 6 / 31 * 100);
  close(bar.width, 3 / 31 * 100);
});

test('bad dates are excluded while valid schedules remain unchanged', () => {
  const valid = Object.freeze(schedule('2033-04-12', '2033-05-01'));
  const rows = Object.freeze([valid, schedule('2033-02-30'), schedule('2033-05-02', '2033-05-01')]);
  const range = buildGanttRange(rows)!;
  assert.equal(iso(range.start), '2033-04-01');
  assert.equal(iso(range.end), '2033-06-01');
  assert.equal(ganttBarFor(rows[1], range), null);
  assert.equal(ganttBarFor(rows[2], range), null);
  assert.deepEqual(valid, schedule('2033-04-12', '2033-05-01'));
});

test('bars clip safely to a supplied horizon instead of extending out of bounds', () => {
  const range = buildGanttRange([schedule('2030-06-01', '2030-06-30')])!;
  assert.deepEqual(ganttBarFor(schedule('2030-05-01', '2030-07-31'), range), { left: 0, width: 100 });
  assert.equal(ganttBarFor(schedule('2031-01-01'), range), null);
  assert.equal(ganttBarFor(schedule('2029-01-01'), range), null);
});
