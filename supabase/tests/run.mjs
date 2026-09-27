import { PGlite } from '@electric-sql/pglite';
import { readFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const db = new PGlite();
try {
  // These fixtures model Supabase's verified JWT identity and database roles.
  // Auth HTTP, Realtime and connection-level races still need Supabase integration tests.
  await db.exec(`
    create role anon nologin;
    create role authenticated nologin;
    create role service_role nologin bypassrls;
    create schema auth;
    create table auth.users(id uuid primary key, email text);
    create function auth.uid() returns uuid language sql stable as $$
      select nullif(current_setting('request.jwt.claims', true)::jsonb->>'sub','')::uuid
    $$;
    create function auth.role() returns text language sql stable as $$
      select current_setting('request.jwt.claims', true)::jsonb->>'role'
    $$;
    grant usage on schema auth to anon, authenticated, service_role;
    grant execute on all functions in schema auth to anon, authenticated, service_role;
  `);
  const migrationDir = path.join(here, '..', 'migrations');
  for (const filename of (await readdir(migrationDir)).filter(n => n.endsWith('.sql')).sort()) {
    await db.exec(await readFile(path.join(migrationDir, filename), 'utf8'));
    console.log(`Applied ${filename}`);
  }
  const results = await db.exec(await readFile(path.join(here, 'security.sql'), 'utf8'));
  let assertions = 0;
  for (const result of results) {
    for (const row of result.rows ?? []) {
      for (const value of Object.values(row)) {
        if (typeof value === 'string' && value.startsWith('PASS:')) {
          console.log(value);
          assertions += 1;
        }
      }
    }
  }
  if (assertions < 25) throw new Error(`Expected at least 25 assertions; got ${assertions}`);
  console.log(`${assertions} database security assertions passed (PGlite PostgreSQL).`);
} finally {
  await db.close();
}

