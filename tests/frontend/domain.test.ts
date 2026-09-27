import { test } from 'node:test';
import assert from 'node:assert/strict';
import { capacityAt, validateHours, nextPhase, portfolioTotals, historicalDelay } from '../../apps/web/lib/domain';
test('overlapping allocations count only for their active dates', () => {
  assert.equal(capacityAt([{resource_id:'r1', hours_per_week:28,start_date:'2026-09-01',end_date:'2026-09-30'}, {resource_id:'r1',hours_per_week:20,start_date:'2026-09-20',end_date:'2026-10-30'}, {resource_id:'r1',hours_per_week:40,start_date:'2027-01-01',end_date:'2027-02-01'}], 'r1', '2026-09-27'), 48);
});
test('timesheets reject negative, nonnumeric, and >24 hours', () => { for (const n of [-1,0,25,NaN,Infinity]) assert.equal(validateHours(n), false); assert.equal(validateHours(7.5),true); });
test('phase progression terminates at launch', () => { assert.equal(nextPhase('EVT'),'DVT'); assert.equal(nextPhase('Ramp/Launch'),null); });
test('portfolio ROI weights expected returns by investment', () => { assert.deepEqual(portfolioTotals([{budget:100,spent:20,roi:2},{budget:300,spent:80,roi:4}]), {budget:400,spent:100,roi:3.5}); });
test('historical delay is absent with no evidence and uses median with outlier', () => { assert.equal(historicalDelay([]),null); assert.equal(historicalDelay([2,4,100]),4); });
