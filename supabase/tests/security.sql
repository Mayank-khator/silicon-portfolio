-- Run on a disposable migrated Supabase database as postgres, or with run.mjs.
-- All fixtures and helper functions are rolled back. UUIDs are test identities only.
begin;
create schema test;
grant usage on schema test to authenticated, service_role;
create function test.assert_true(condition boolean, description text) returns text
language plpgsql as $$ begin
  if condition is not true then raise exception 'FAIL: %', description; end if;
  return 'PASS: ' || description;
end $$;
create function test.expect_error(statement text, expected_code text, description text) returns text
language plpgsql as $$
declare actual_code text;
begin
  begin execute statement;
  exception when others then
    get stacked diagnostics actual_code = returned_sqlstate;
    if actual_code <> expected_code then raise exception 'FAIL: % expected %, got % (%)', description,expected_code,actual_code,sqlerrm; end if;
    return 'PASS: ' || description;
  end;
  raise exception 'FAIL: % did not raise %', description,expected_code;
end $$;
grant execute on all functions in schema test to authenticated, service_role;

set local request.jwt.claims = '{"role":"service_role"}';
insert into auth.users(id,email) values
('00000000-0000-0000-0000-000000000001','manager-a@example.test'),
('00000000-0000-0000-0000-000000000002','engineer-a@example.test'),
('00000000-0000-0000-0000-000000000003','qa-a@example.test'),
('00000000-0000-0000-0000-000000000004','manager-b@example.test'),
('00000000-0000-0000-0000-000000000005','architect-a@example.test'),
('00000000-0000-0000-0000-000000000006','sponsor-a@example.test');
insert into public.tenants(id,name) values
('10000000-0000-0000-0000-000000000001','Test tenant A'),
('10000000-0000-0000-0000-000000000002','Test tenant B');
insert into public.memberships(tenant_id,user_id,role) values
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','fab_manager'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','engineer'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000003','qa_engineer'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000005','lead_architect'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000006','exec_sponsor'),
('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000004','fab_manager');
insert into public.projects(id,tenant_id,code,name,stage,start_date,end_date) values
('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','A1','Project A','EVT','2026-01-01','2026-12-31'),
('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','B1','Project B','Ideation','2026-01-01','2026-12-31');
insert into public.tasks(id,tenant_id,project_id,title,stage,start_date,end_date,assigned_to) values
('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','Assigned A','EVT','2026-01-01','2026-06-30','00000000-0000-0000-0000-000000000002');

set local role authenticated;
set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000002"}';
select test.assert_true((select count(*) = 1 from public.projects), 'Tenant A cannot read Tenant B projects');
select test.assert_true((select count(*) = 1 from public.tenants), 'Tenant list is membership scoped');
select test.assert_true((select count(*) = 5 from public.memberships), 'Membership reads are tenant scoped');
select test.expect_error($q$update public.memberships set role='fab_manager' where user_id=auth.uid()$q$,'42501','Clients cannot self-escalate membership');
select test.expect_error($q$insert into public.memberships(tenant_id,user_id,role) values ('10000000-0000-0000-0000-000000000002',auth.uid(),'fab_manager')$q$,'42501','Clients cannot join another tenant');
select test.expect_error($q$insert into public.projects(tenant_id,code,name,start_date,end_date) values ('10000000-0000-0000-0000-000000000001','BAD','Denied','2026-01-01','2026-12-31')$q$,'42501','Engineer cannot create projects');
update public.projects set budget=999 where id='20000000-0000-0000-0000-000000000001';
select test.assert_true((select budget = 0 from public.projects where id='20000000-0000-0000-0000-000000000001'),'Engineer project update is denied by RLS');
update public.tasks set status='in_progress',progress=25 where id='30000000-0000-0000-0000-000000000001' and version=1;
select test.assert_true((select version = 2 and progress = 25 from public.tasks where id='30000000-0000-0000-0000-000000000001'),'Assigned engineer updates status and server increments version');
select test.expect_error($q$update public.tasks set title='Stolen planning' where id='30000000-0000-0000-0000-000000000001'$q$,'42501','Engineer cannot edit task planning fields');
select test.expect_error($q$select public.patch_record('tasks','30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,'{"progress":50}')$q$,'40001','Stale version RPC fails');
update public.tasks set progress=90 where id='30000000-0000-0000-0000-000000000001' and version=1;
select test.assert_true((select version = 2 and progress = 25 from public.tasks where id='30000000-0000-0000-0000-000000000001'),'Stale direct PATCH filter changes nothing');
select test.assert_true((public.patch_record('tasks','30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',2,'{"progress":40}')->>'version')::int=3,'Matching optimistic RPC updates one version');
select test.expect_error($q$select public.patch_record('tasks','30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',3,'{"tenant_id":"10000000-0000-0000-0000-000000000002"}')$q$,'22023','Optimistic RPC rejects metadata fields');

select test.expect_error($q$update public.audit_logs set operation='DELETE'$q$,'42501','Authenticated users cannot alter audit');
select test.expect_error($q$delete from public.audit_logs$q$,'42501','Authenticated users cannot delete audit');
select test.expect_error($q$insert into public.audit_logs(tenant_id,entity,record_id,operation) values ('10000000-0000-0000-0000-000000000001','projects','20000000-0000-0000-0000-000000000001','INSERT')$q$,'42501','Authenticated users cannot forge audit');
select test.expect_error($q$truncate public.audit_logs$q$,'42501','Authenticated users cannot truncate audit');
select test.expect_error($q$select * from public.outbox$q$,'42501','Clients cannot read the transactional outbox');
select test.expect_error($q$select * from public.claim_outbox_events(10,'unauthorized')$q$,'42501','Clients cannot call worker RPC');

select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2026-05-01',-1)$q$,'23514','Negative time is rejected');
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2026-05-01',1.1)$q$,'23514','Non-quarter-hour time is rejected');
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2026-05-01',0.251)$q$,'23514','Sub-cent precision cannot round around the quarter-hour rule');
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2027-05-01',1)$q$,'23514','Time outside project dates is rejected');
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,task_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','EVT','2026-07-01',1)$q$,'23514','Time outside task dates is rejected');
insert into public.time_entries(id,tenant_id,project_id,phase,work_date,hours,status) values
('40000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2026-05-01',20,'submitted');
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','EVT','2026-05-01',5)$q$,'23514','Daily total cannot exceed 24 hours');
select test.expect_error($q$update public.time_entries set status='approved' where id='40000000-0000-0000-0000-000000000001'$q$,'42501','Engineer cannot approve own submitted time');
select test.expect_error($q$update public.time_entries set hours=1 where id='40000000-0000-0000-0000-000000000001'$q$,'42501','Submitted time cannot be silently edited');

set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000001"}';
select test.expect_error($q$insert into public.tasks(tenant_id,project_id,title,start_date,end_date) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002','Cross tenant','2026-01-01','2026-12-31')$q$,'23503','Composite project FK rejects cross-tenant task');
select test.expect_error($q$update public.projects set tenant_id='10000000-0000-0000-0000-000000000002' where id='20000000-0000-0000-0000-000000000001'$q$,'42501','Tenant ownership cannot be changed');
select test.expect_error($q$update public.projects set stage='PVT' where id='20000000-0000-0000-0000-000000000001'$q$,'23514','NPI stage skipping is rejected');
select test.expect_error($q$update public.projects set stage='DVT' where id='20000000-0000-0000-0000-000000000001'$q$,'23514','DVT requires an approved design freeze');
update public.time_entries set status='approved' where id='40000000-0000-0000-0000-000000000001';
select test.assert_true((select approved_by=auth.uid() and status='approved' from public.time_entries where id='40000000-0000-0000-0000-000000000001'),'Manager approves another member time with verified approver');

set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000005"}';
select test.expect_error($q$update public.projects set design_frozen=true where id='20000000-0000-0000-0000-000000000001'$q$,'42501','Lead architect cannot self-approve design freeze');
set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000003"}';
select test.expect_error($q$update public.projects set budget=200 where id='20000000-0000-0000-0000-000000000001'$q$,'42501','QA cannot alter project budget');
update public.projects set design_frozen=true,freeze_approved_by='00000000-0000-0000-0000-000000000001' where id='20000000-0000-0000-0000-000000000001';
select test.assert_true((select design_frozen and freeze_approved_by=auth.uid() from public.projects where id='20000000-0000-0000-0000-000000000001'),'QA freeze records actual caller, ignoring forged approver');

set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000001"}';
update public.projects set stage='DVT' where id='20000000-0000-0000-0000-000000000001';
select test.assert_true((select stage='DVT' from public.projects where id='20000000-0000-0000-0000-000000000001'),'Approved project advances one stage');
select test.expect_error($q$update public.projects set design_frozen=false where id='20000000-0000-0000-0000-000000000001'$q$,'23514','DVT cannot remove its approved design freeze');
select test.expect_error($q$update public.projects set stage='EVT' where id='20000000-0000-0000-0000-000000000001'$q$,'23514','NPI stage regression is rejected');

set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000006"}';
insert into public.demands(tenant_id,title) values ('10000000-0000-0000-0000-000000000001','Sponsor proposal');
select test.assert_true((select count(*)=1 from public.demands),'Executive sponsor may submit investment demand');
update public.projects set budget=999 where id='20000000-0000-0000-0000-000000000001';
select test.assert_true((select budget=0 from public.projects where id='20000000-0000-0000-0000-000000000001'),'Executive sponsor cannot edit project plan');
insert into public.reports(tenant_id,title,report_data) values ('10000000-0000-0000-0000-000000000001','Test report','{"synthetic":true}');
select test.assert_true((select count(*)=1 from public.reports),'Tenant member can save and read own generated report');

set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000004"}';
select test.assert_true((select count(*)=0 from public.reports),'Another tenant cannot read reports');
select test.assert_true(not exists(select 1 from public.audit_logs where tenant_id='10000000-0000-0000-0000-000000000001'),'Another tenant cannot read audit records');

reset role;
set local request.jwt.claims = '{"role":"service_role"}';
select test.assert_true((select count(*) from public.outbox)=(select count(*) from public.audit_logs),'Every audited mutation has one transactional outbox row');
select test.expect_error($q$delete from public.audit_logs$q$,'42501','Audit trigger rejects even ordinary postgres deletion');
select test.assert_true(exists(select 1 from public.audit_logs where entity='projects' and operation='UPDATE' and actor_id='00000000-0000-0000-0000-000000000003' and new_data->>'design_frozen'='true'),'Audit captures verified freeze actor and new values');
savepoint rollback_check;
insert into public.demands(tenant_id,title) values ('10000000-0000-0000-0000-000000000001','Rollback demand');
rollback to rollback_check;
select test.assert_true(not exists(select 1 from public.outbox where payload->'data'->>'title'='Rollback demand'),'Rolled-back mutations leave no outbox events');
select test.assert_true(not exists(select 1 from public.audit_logs where new_data->>'title'='Rollback demand'),'Rolled-back mutations leave no audit events');

-- Use relative project dates so future-day tests stay valid after this year.
insert into public.projects(id,tenant_id,code,name,start_date,end_date) values
('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000001','FUTURE','Date boundary fixture',
 (current_timestamp at time zone 'UTC')::date - 1,(current_timestamp at time zone 'UTC')::date + 2);
set local role authenticated;
set local request.jwt.claims = '{"role":"authenticated","sub":"00000000-0000-0000-0000-000000000002"}';
select test.expect_error($q$insert into public.time_entries(tenant_id,project_id,phase,work_date,hours) values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','Ideation',(current_timestamp at time zone 'UTC')::date+1,1)$q$,'23514','Future work dates inside project range are rejected');
insert into public.time_entries(id,tenant_id,project_id,phase,work_date,hours) values
('40000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','Ideation',(current_timestamp at time zone 'UTC')::date,0.25);
select test.assert_true((select hours=0.25 from public.time_entries where id='40000000-0000-0000-0000-000000000002'),'A quarter hour on the current UTC day is accepted');
select test.expect_error($q$update public.time_entries set work_date=(current_timestamp at time zone 'UTC')::date+1 where id='40000000-0000-0000-0000-000000000002'$q$,'23514','Direct update cannot move time into the future');
select test.expect_error($q$update public.time_entries set hours=0.3 where id='40000000-0000-0000-0000-000000000002'$q$,'23514','Direct update cannot bypass quarter-hour precision');
reset role;
set local request.jwt.claims = '{"role":"service_role"}';

set local role service_role;
select test.expect_error($q$insert into public.audit_logs(tenant_id,entity,record_id,operation) values ('10000000-0000-0000-0000-000000000001','projects','20000000-0000-0000-0000-000000000001','INSERT')$q$,'42501','Worker service role cannot forge audit records');
create temporary table claimed as select * from public.claim_outbox_events(2,'test-worker');
select test.assert_true((select count(*)=2 and min(attempts)=1 from claimed),'Worker atomically claims events and increments attempts');
select test.assert_true(not public.acknowledge_outbox_event((select id from claimed limit 1),'other-worker'),'Another worker cannot acknowledge an active lease');
select test.assert_true(public.acknowledge_outbox_event((select id from claimed limit 1),'test-worker'),'Lease owner can acknowledge event');
select test.assert_true(public.fail_outbox_event((select c.id from claimed c join public.outbox o on o.id=c.id where o.status='processing' limit 1),'test-worker','Synthetic broker failure'),'Lease owner can requeue failed publish');
select test.assert_true(exists(select 1 from public.outbox where status='pending' and last_error='Synthetic broker failure' and available_at > now()),'Failed publication receives retry backoff');
reset role;
rollback;
