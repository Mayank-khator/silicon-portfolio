-- Intentionally does not create users, tenants or credentials.
-- After `supabase start` / `supabase db reset`, bootstrap a development user:
-- python supabase/scripts/bootstrap_demo.py --email YOUR_DEVELOPMENT_EMAIL
-- See docs/database.md. The script requires environment-provided credentials.
do $$ begin
  raise notice 'No automatic demo identities created. Run supabase/scripts/bootstrap_demo.py explicitly.';
end $$;

