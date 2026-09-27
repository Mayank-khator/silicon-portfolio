-- Silicon Portfolio: tenant boundaries are enforced in PostgreSQL.
-- Authentication is supplied by Supabase Auth; never trust an application role header.
begin;

create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated, service_role;

create table public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) between 1 and 160),
  created_at timestamptz not null default now()
);

create table public.memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  user_id uuid not null references auth.users(id),
  role text not null check (role in ('fab_manager','lead_architect','qa_engineer','exec_sponsor','engineer')),
  created_at timestamptz not null default now(),
  unique (tenant_id, user_id),
  unique (tenant_id, id)
);
create index memberships_user_idx on public.memberships(user_id, tenant_id);

-- Definer helpers bypass membership RLS without causing recursive policies.
-- Neither accepts a user id: the identity always comes from the verified JWT.
create function private.is_member(p_tenant_id uuid)
returns boolean language sql stable security definer set search_path = ''
as $$ select exists(select 1 from public.memberships m where m.tenant_id = p_tenant_id and m.user_id = auth.uid()) $$;

create function private.has_role(p_tenant_id uuid, p_roles text[])
returns boolean language sql stable security definer set search_path = ''
as $$ select exists(select 1 from public.memberships m where m.tenant_id = p_tenant_id and m.user_id = auth.uid() and m.role = any(p_roles)) $$;

create function private.is_service()
returns boolean language sql stable security invoker set search_path = ''
as $$ select coalesce(auth.role(), '') = 'service_role' $$;

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  code text not null check (length(trim(code)) between 1 and 40),
  name text not null check (length(trim(name)) between 1 and 200),
  node text not null default '7nm',
  stage text not null default 'Ideation' check (stage in ('Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch')),
  status text not null default 'on_track' check (status in ('on_track','at_risk','delayed')),
  progress numeric not null default 0 check (progress between 0 and 100),
  budget numeric(18,2) not null default 0 check (budget >= 0),
  spent numeric(18,2) not null default 0 check (spent >= 0),
  roi numeric not null default 0,
  start_date date not null,
  end_date date not null,
  owner text not null default '',
  owner_id uuid,
  strategic_alignment numeric not null default 50 check (strategic_alignment between 0 and 100),
  design_frozen boolean not null default false,
  freeze_approved_by uuid references auth.users(id),
  freeze_approved_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, code),
  foreign key (tenant_id, owner_id) references public.memberships(tenant_id, user_id),
  check (end_date >= start_date),
  check ((design_frozen and freeze_approved_by is not null and freeze_approved_at is not null)
      or (not design_frozen and freeze_approved_by is null and freeze_approved_at is null))
);

create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  project_id uuid not null,
  title text not null check (length(trim(title)) between 1 and 240),
  stage text not null default 'Ideation' check (stage in ('Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch')),
  status text not null default 'todo' check (status in ('todo','in_progress','done')),
  start_date date not null,
  end_date date not null,
  progress numeric not null default 0 check (progress between 0 and 100),
  assigned_to uuid,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, project_id, id),
  foreign key (tenant_id, project_id) references public.projects(tenant_id, id),
  foreign key (tenant_id, assigned_to) references public.memberships(tenant_id, user_id),
  check (end_date >= start_date)
);

create table public.demands (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  title text not null check (length(trim(title)) between 1 and 240),
  category text not null default 'New Product',
  node text not null default '7nm',
  estimated_budget numeric(18,2) not null default 0 check (estimated_budget >= 0),
  strategic_score numeric not null default 50 check (strategic_score between 0 and 100),
  status text not null default 'submitted' check (status in ('submitted','under_review','approved','rejected','converted')),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id)
);

create table public.resources (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  user_id uuid,
  name text not null check (length(trim(name)) between 1 and 160),
  role text not null,
  skills text[] not null default '{}',
  fab_nodes text[] not null default '{}',
  weekly_capacity numeric not null default 40 check (weekly_capacity > 0 and weekly_capacity <= 168),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, user_id) references public.memberships(tenant_id, user_id)
);

create table public.allocations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  resource_id uuid not null,
  project_id uuid not null,
  hours_per_week numeric not null check (hours_per_week > 0 and hours_per_week <= 168),
  start_date date not null,
  end_date date not null,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, resource_id) references public.resources(tenant_id, id),
  foreign key (tenant_id, project_id) references public.projects(tenant_id, id),
  check (end_date >= start_date)
);

create table public.time_entries (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  user_id uuid not null default auth.uid(),
  project_id uuid not null,
  task_id uuid,
  phase text not null check (phase in ('Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch')),
  work_date date not null,
  -- Unconstrained numeric avoids rounding invalid inputs such as 0.251 to 0.25
  -- before the quarter-hour invariant can reject them.
  hours numeric not null check (hours > 0 and hours <= 24 and mod(hours, 0.25) = 0),
  billable boolean not null default true,
  note text not null default '' check (length(note) <= 4000),
  status text not null default 'draft' check (status in ('draft','submitted','approved','rejected')),
  approved_by uuid references auth.users(id),
  approved_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, user_id) references public.memberships(tenant_id, user_id),
  foreign key (tenant_id, project_id) references public.projects(tenant_id, id),
  foreign key (tenant_id, project_id, task_id) references public.tasks(tenant_id, project_id, id),
  check ((status = 'approved' and approved_by is not null and approved_at is not null)
      or (status <> 'approved' and approved_by is null and approved_at is null))
);
create index time_entries_user_date_idx on public.time_entries(tenant_id, user_id, work_date);

create table public.historical_phase_metrics (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  project_id uuid,
  node text not null,
  phase text not null check (phase in ('Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch')),
  planned_days numeric not null check (planned_days > 0),
  actual_days numeric not null check (actual_days > 0),
  completed_at timestamptz not null,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, project_id) references public.projects(tenant_id, id)
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  report_type text not null default 'portfolio',
  title text not null default 'Portfolio report',
  report_data jsonb not null default '{}',
  status text not null default 'complete' check (status in ('pending','complete','failed')),
  created_by uuid not null default auth.uid(),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, created_by) references public.memberships(tenant_id, user_id)
);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  actor_id uuid,
  entity text not null,
  record_id uuid not null,
  operation text not null check (operation in ('INSERT','UPDATE','DELETE')),
  previous_data jsonb,
  new_data jsonb,
  occurred_at timestamptz not null default clock_timestamp()
);
create index audit_logs_tenant_time_idx on public.audit_logs(tenant_id, occurred_at desc);

create table public.outbox (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id),
  event_type text not null,
  payload jsonb not null,
  status text not null default 'pending' check (status in ('pending','processing','published','dead')),
  attempts integer not null default 0,
  available_at timestamptz not null default now(),
  locked_by text,
  locked_until timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  published_at timestamptz
);
create index outbox_ready_idx on public.outbox(status, available_at, created_at);

-- Protect metadata before the domain guards; version is server-maintained.
create function private.guard_version()
returns trigger language plpgsql set search_path = '' as $$
begin
  if tg_op = 'INSERT' then
    new.version := 1;
    new.created_at := now();
  else
    if new.id <> old.id or new.tenant_id <> old.tenant_id then
      raise exception using errcode = '42501', message = 'Record identity and tenant are immutable';
    end if;
    new.version := old.version + 1;
    new.created_at := old.created_at;
  end if;
  new.updated_at := now();
  return new;
end $$;

create function private.guard_project()
returns trigger language plpgsql set search_path = '' as $$
declare
  stages constant text[] := array['Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch'];
  approver boolean := private.has_role(new.tenant_id, array['fab_manager','qa_engineer']);
begin
  if private.is_service() then return new; end if;
  if tg_op = 'INSERT' then
    if new.stage <> 'Ideation' or new.design_frozen then
      raise exception using errcode = '42501', message = 'New projects must begin in Ideation without freeze approval';
    end if;
    new.freeze_approved_by := null;
    new.freeze_approved_at := null;
  else
    -- QA can approve a freeze but cannot change budgets, dates, ownership or stage.
    if not private.has_role(new.tenant_id, array['fab_manager','lead_architect'])
       and (to_jsonb(new) - array['design_frozen','freeze_approved_by','freeze_approved_at','version','updated_at'])
           is distinct from (to_jsonb(old) - array['design_frozen','freeze_approved_by','freeze_approved_at','version','updated_at']) then
      raise exception using errcode = '42501', message = 'Project planning requires a fab manager or lead architect';
    end if;
    if new.design_frozen is distinct from old.design_frozen then
      if not approver then raise exception using errcode = '42501', message = 'Freeze approval requires QA or fab manager'; end if;
      if new.design_frozen then
        if array_position(stages, old.stage) < 3 then
          raise exception using errcode = '23514', message = 'Freeze approval is available from EVT';
        end if;
        new.freeze_approved_by := auth.uid();
        new.freeze_approved_at := now();
      else
        if array_position(stages, old.stage) >= 4 then
          raise exception using errcode = '23514', message = 'A project in DVT or later cannot remove its approved freeze';
        end if;
        new.freeze_approved_by := null;
        new.freeze_approved_at := null;
      end if;
    else
      new.freeze_approved_by := old.freeze_approved_by;
      new.freeze_approved_at := old.freeze_approved_at;
    end if;
    if new.stage is distinct from old.stage then
      if array_position(stages, new.stage) <> array_position(stages, old.stage) + 1 then
        raise exception using errcode = '23514', message = 'NPI phases must advance exactly one stage';
      end if;
      if array_position(stages, new.stage) >= 4 and not new.design_frozen then
        raise exception using errcode = '23514', message = 'Design freeze approval is required before DVT';
      end if;
    end if;
  end if;
  return new;
end $$;

create function private.guard_task()
returns trigger language plpgsql set search_path = '' as $$
begin
  if tg_op = 'UPDATE' and not private.is_service()
     and not private.has_role(new.tenant_id, array['fab_manager','lead_architect','qa_engineer']) then
    if (to_jsonb(new) - array['status','progress','version','updated_at'])
       is distinct from (to_jsonb(old) - array['status','progress','version','updated_at']) then
      raise exception using errcode = '42501', message = 'Engineers may update only status and progress of assigned tasks';
    end if;
  end if;
  return new;
end $$;

create function private.guard_time_entry()
returns trigger language plpgsql set search_path = '' as $$
declare
  total_hours numeric;
  can_approve boolean := private.has_role(new.tenant_id, array['fab_manager','lead_architect']);
  date_start date;
  date_end date;
begin
  if new.work_date > (current_timestamp at time zone 'UTC')::date then
    raise exception using errcode = '23514', message = 'Time cannot be logged for a future UTC day';
  end if;
  if not private.is_service() then
    if tg_op = 'INSERT' then
      if new.user_id <> auth.uid() or new.status not in ('draft','submitted') then
        raise exception using errcode = '42501', message = 'Create only your own draft or submitted time';
      end if;
      new.approved_by := null;
      new.approved_at := null;
    else
      if new.user_id <> old.user_id then raise exception using errcode = '42501', message = 'Time entry owner is immutable'; end if;
      if new.status in ('approved','rejected') and new.status is distinct from old.status then
        if not can_approve or old.user_id = auth.uid() or old.status <> 'submitted' then
          raise exception using errcode = '42501', message = 'A different manager must review submitted time';
        end if;
        if (to_jsonb(new) - array['status','approved_by','approved_at','version','updated_at'])
           is distinct from (to_jsonb(old) - array['status','approved_by','approved_at','version','updated_at']) then
          raise exception using errcode = '42501', message = 'Review may change only the time entry status';
        end if;
        if new.status = 'approved' then
          new.approved_by := auth.uid(); new.approved_at := now();
        else
          new.approved_by := null; new.approved_at := null;
        end if;
      else
        if old.user_id <> auth.uid() or old.status not in ('draft','rejected') or new.status not in ('draft','submitted') then
          raise exception using errcode = '42501', message = 'Only the owner may edit draft or rejected time';
        end if;
        new.approved_by := null; new.approved_at := null;
      end if;
    end if;
  end if;
  select p.start_date, p.end_date into date_start, date_end from public.projects p
    where p.tenant_id = new.tenant_id and p.id = new.project_id;
  if new.work_date not between date_start and date_end then
    raise exception using errcode = '23514', message = 'Time entry must be within project dates';
  end if;
  if new.task_id is not null then
    select t.start_date, t.end_date into date_start, date_end from public.tasks t
      where t.tenant_id = new.tenant_id and t.project_id = new.project_id and t.id = new.task_id;
    if new.work_date not between date_start and date_end then
      raise exception using errcode = '23514', message = 'Time entry must be within task dates';
    end if;
  end if;
  -- Serialize same-user/day mutations across projects to enforce daily bounds.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.tenant_id::text || ':' || new.user_id::text || ':' || new.work_date::text, 0));
  select coalesce(sum(t.hours), 0) into total_hours from public.time_entries t
    where t.tenant_id = new.tenant_id and t.user_id = new.user_id and t.work_date = new.work_date and t.id <> new.id;
  if total_hours + new.hours > 24 then
    raise exception using errcode = '23514', message = 'Total daily time cannot exceed 24 hours';
  end if;
  return new;
end $$;

create function private.record_mutation()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  record_data jsonb;
  old_data jsonb;
  tenant uuid;
  record uuid;
begin
  if tg_op <> 'DELETE' then record_data := to_jsonb(new); end if;
  if tg_op <> 'INSERT' then old_data := to_jsonb(old); end if;
  record := coalesce(record_data->>'id', old_data->>'id')::uuid;
  tenant := coalesce(record_data->>'tenant_id', old_data->>'tenant_id')::uuid;
  if tg_table_name = 'tenants' then tenant := record; end if;
  insert into public.audit_logs(tenant_id, actor_id, entity, record_id, operation, previous_data, new_data)
    values (tenant, auth.uid(), tg_table_name, record, tg_op, old_data, record_data);
  insert into public.outbox(tenant_id, event_type, payload)
    values (tenant, tg_table_name || '.' || lower(tg_op), jsonb_build_object(
      'tenant_id',tenant,'entity',tg_table_name,'record_id',record,'operation',tg_op,
      'actor_id',auth.uid(),'data',record_data,'previous',old_data));
  return coalesce(new, old);
end $$;

create function private.reject_audit_mutation()
returns trigger language plpgsql set search_path = '' as $$
begin raise exception using errcode = '42501', message = 'Audit records are append-only'; end $$;
create trigger audit_logs_immutable before update or delete on public.audit_logs
  for each row execute function private.reject_audit_mutation();
create trigger audit_logs_no_truncate before truncate on public.audit_logs
  for each statement execute function private.reject_audit_mutation();

do $$ declare entity text; begin
  foreach entity in array array['projects','tasks','demands','resources','allocations','time_entries','historical_phase_metrics','reports'] loop
    execute format('create trigger a_guard_version before insert or update on public.%I for each row execute function private.guard_version()', entity);
    execute format('create trigger z_record_mutation after insert or update or delete on public.%I for each row execute function private.record_mutation()', entity);
    execute format('create index %I on public.%I(tenant_id)', entity || '_tenant_idx', entity);
  end loop;
  foreach entity in array array['tenants','memberships'] loop
    execute format('create trigger z_record_mutation after insert or update or delete on public.%I for each row execute function private.record_mutation()', entity);
  end loop;
end $$;
create trigger b_guard_project before insert or update on public.projects for each row execute function private.guard_project();
create trigger b_guard_task before insert or update on public.tasks for each row execute function private.guard_task();
create trigger b_guard_time before insert or update on public.time_entries for each row execute function private.guard_time_entry();

-- RLS remains authoritative even when the API is bypassed.
do $$ declare entity text; begin
  foreach entity in array array['tenants','memberships','projects','tasks','demands','resources','allocations','time_entries','historical_phase_metrics','reports','audit_logs','outbox'] loop
    execute format('alter table public.%I enable row level security', entity);
    execute format('revoke all on public.%I from anon, authenticated', entity);
    execute format('grant all on public.%I to service_role', entity);
  end loop;
  foreach entity in array array['memberships','projects','tasks','demands','resources','allocations','time_entries','historical_phase_metrics','reports','audit_logs'] loop
    execute format('grant select on public.%I to authenticated', entity);
    execute format('create policy tenant_read on public.%I for select to authenticated using (private.is_member(tenant_id))', entity);
  end loop;
  foreach entity in array array['projects','tasks','demands','resources','allocations','time_entries','historical_phase_metrics'] loop
    execute format('grant insert, update, delete on public.%I to authenticated', entity);
  end loop;
end $$;
grant select on public.tenants to authenticated;
create policy tenant_read on public.tenants for select to authenticated using (private.is_member(id));

create policy project_insert on public.projects for insert to authenticated with check (private.has_role(tenant_id,array['fab_manager','lead_architect']));
create policy project_update on public.projects for update to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer'])) with check (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer']));
create policy project_delete on public.projects for delete to authenticated using (private.has_role(tenant_id,array['fab_manager']));

create policy task_insert on public.tasks for insert to authenticated with check (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer']));
create policy task_update on public.tasks for update to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer']) or (private.is_member(tenant_id) and assigned_to = auth.uid())) with check (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer']) or (private.is_member(tenant_id) and assigned_to = auth.uid()));
create policy task_delete on public.tasks for delete to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect','qa_engineer']));

create policy demand_write on public.demands for all to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect','exec_sponsor'])) with check (private.has_role(tenant_id,array['fab_manager','lead_architect','exec_sponsor']));
create policy resource_write on public.resources for all to authenticated using (private.has_role(tenant_id,array['fab_manager'])) with check (private.has_role(tenant_id,array['fab_manager']));
create policy allocation_write on public.allocations for all to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect'])) with check (private.has_role(tenant_id,array['fab_manager','lead_architect']));
create policy historical_write on public.historical_phase_metrics for all to authenticated using (private.has_role(tenant_id,array['fab_manager','lead_architect'])) with check (private.has_role(tenant_id,array['fab_manager','lead_architect']));
create policy time_insert on public.time_entries for insert to authenticated with check (private.is_member(tenant_id) and user_id = auth.uid() and status in ('draft','submitted'));
create policy time_update on public.time_entries for update to authenticated using (private.is_member(tenant_id) and (user_id = auth.uid() or private.has_role(tenant_id,array['fab_manager','lead_architect']))) with check (private.is_member(tenant_id) and (user_id = auth.uid() or private.has_role(tenant_id,array['fab_manager','lead_architect'])));
create policy time_delete on public.time_entries for delete to authenticated using (private.is_member(tenant_id) and user_id = auth.uid() and status = 'draft');

-- Authenticated callers may save their own generated report; reports are read-only afterward.
grant insert on public.reports to authenticated;
create policy report_insert on public.reports for insert to authenticated with check (private.is_member(tenant_id) and created_by = auth.uid());

-- A convenience optimistic mutation RPC. It is invoker-security and observes RLS.
-- Direct PostgREST PATCH must also include an equality filter on the expected version.
create function public.patch_record(p_entity text, p_id uuid, p_tenant_id uuid, p_expected_version integer, p_changes jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare current_row jsonb; updated_row jsonb; fields text; allowed text[]; key text;
begin
  allowed := case p_entity
    when 'projects' then array['name','code','node','stage','status','progress','budget','spent','roi','start_date','end_date','owner','owner_id','strategic_alignment','design_frozen']
    when 'tasks' then array['project_id','title','stage','status','start_date','end_date','progress','assigned_to']
    when 'demands' then array['title','category','node','estimated_budget','strategic_score','status']
    when 'resources' then array['user_id','name','role','skills','fab_nodes','weekly_capacity']
    when 'allocations' then array['resource_id','project_id','hours_per_week','start_date','end_date']
    when 'time_entries' then array['project_id','task_id','phase','work_date','hours','billable','note','status']
    when 'historical_phase_metrics' then array['project_id','node','phase','planned_days','actual_days','completed_at']
    else null end;
  if allowed is null or p_changes is null or jsonb_typeof(p_changes) <> 'object' or p_changes = '{}'::jsonb or p_expected_version is null or p_expected_version < 1 then
    raise exception using errcode = '22023', message = 'Unsupported entity, empty changes or missing version';
  end if;
  for key in select jsonb_object_keys(p_changes) loop
    if not key = any(allowed) then raise exception using errcode = '22023', message = 'Unsupported patch field: ' || key; end if;
  end loop;
  execute format('select to_jsonb(t) from public.%I t where id=$1 and tenant_id=$2 for update', p_entity)
    into current_row using p_id,p_tenant_id;
  if current_row is null then raise exception using errcode = 'P0002', message = 'Record not found or inaccessible'; end if;
  if (current_row->>'version')::integer <> p_expected_version then
    raise exception using errcode = '40001', message = 'Version conflict; reload before updating';
  end if;
  select string_agg(format('%I = proposed.%I', k, k), ', ') into fields from jsonb_object_keys(p_changes) k;
  execute format('update public.%I t set %s from jsonb_populate_record(null::public.%I, $1) proposed where t.id=$2 and t.tenant_id=$3 returning to_jsonb(t)',p_entity,fields,p_entity)
    into updated_row using current_row || p_changes,p_id,p_tenant_id;
  if updated_row is null then raise exception using errcode = '42501', message = 'Update not permitted'; end if;
  return updated_row;
end $$;

-- Worker claims use SKIP LOCKED and leases. Publish is at-least-once: dedupe by id.
create function public.claim_outbox_events(p_limit integer, p_worker_id text)
returns table(id uuid, event_type text, payload jsonb, attempts integer)
language plpgsql security definer set search_path = '' as $$
begin
  if not private.is_service() then raise exception using errcode = '42501', message = 'Worker service role required'; end if;
  if p_worker_id is null or length(p_worker_id) not between 1 and 200 or p_limit is null or p_limit not between 1 and 100 then
    raise exception using errcode = '22023', message = 'A worker id and limit between 1 and 100 are required';
  end if;
  -- Also cap crashed workers, whose expired leases would otherwise retry forever.
  update public.outbox o set status = 'dead', locked_by = null, locked_until = null,
    last_error = coalesce(o.last_error, 'Delivery lease expired after maximum attempts')
    where o.attempts >= 8 and (o.status = 'pending' or (o.status = 'processing' and o.locked_until <= now()));
  return query
    with candidates as (
      select o.id from public.outbox o where o.attempts < 8 and
        ((o.status = 'pending' and o.available_at <= now()) or (o.status = 'processing' and o.locked_until <= now()))
      order by o.created_at for update skip locked limit p_limit
    )
    update public.outbox o set status = 'processing', locked_by = p_worker_id,
      locked_until = now() + interval '60 seconds', attempts = o.attempts + 1
    from candidates c where o.id = c.id
    returning o.id, o.event_type, o.payload, o.attempts;
end $$;

create function public.acknowledge_outbox_event(p_id uuid, p_worker_id text)
returns boolean language plpgsql security definer set search_path = '' as $$
declare changed integer;
begin
  if not private.is_service() then raise exception using errcode = '42501', message = 'Worker service role required'; end if;
  update public.outbox set status = 'published', published_at = now(), locked_by = null, locked_until = null, last_error = null
    where id = p_id and status = 'processing' and locked_by = p_worker_id and locked_until > now();
  get diagnostics changed = row_count;
  return changed = 1;
end $$;

create function public.fail_outbox_event(p_id uuid, p_worker_id text, p_error text)
returns boolean language plpgsql security definer set search_path = '' as $$
declare changed integer;
begin
  if not private.is_service() then raise exception using errcode = '42501', message = 'Worker service role required'; end if;
  update public.outbox set status = case when attempts >= 8 then 'dead' else 'pending' end,
    available_at = now() + least(3600, power(2, attempts)::integer) * interval '1 second',
    last_error = left(coalesce(p_error,'Unknown publish failure'),2000), locked_by = null, locked_until = null
    where id = p_id and status = 'processing' and locked_by = p_worker_id and locked_until > now();
  get diagnostics changed = row_count;
  return changed = 1;
end $$;

-- Defaults are explicit: no client privilege to provision tenants/memberships,
-- alter roles, forge audit events, access outbox or execute definer triggers.
revoke all on all functions in schema private from public, anon, authenticated;
grant execute on function private.is_member(uuid), private.has_role(uuid,text[]), private.is_service() to authenticated, service_role;
revoke all on function public.patch_record(text,uuid,uuid,integer,jsonb) from public, anon;
grant execute on function public.patch_record(text,uuid,uuid,integer,jsonb) to authenticated, service_role;
revoke all on function public.claim_outbox_events(integer,text), public.acknowledge_outbox_event(uuid,text), public.fail_outbox_event(uuid,text,text) from public, anon, authenticated;
grant execute on function public.claim_outbox_events(integer,text), public.acknowledge_outbox_event(uuid,text), public.fail_outbox_event(uuid,text,text) to service_role;
revoke insert, update, delete, truncate on public.audit_logs from authenticated, anon, service_role;
grant select on public.audit_logs to service_role;
alter default privileges in schema private revoke execute on functions from public;

-- Publish only tenant-readable domain tables. Membership revocation requires a
-- session refresh/reconnect in the client; never publish the worker outbox.
do $$ declare entity text; begin
  if not exists (select 1 from pg_catalog.pg_publication where pubname = 'supabase_realtime') then
    create publication supabase_realtime;
  end if;
  foreach entity in array array['projects','tasks','demands','resources','allocations','time_entries','historical_phase_metrics','reports','audit_logs'] loop
    execute format('alter publication supabase_realtime add table public.%I', entity);
  end loop;
end $$;
commit;
