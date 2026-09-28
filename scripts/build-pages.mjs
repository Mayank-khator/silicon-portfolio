import { spawnSync } from 'node:child_process';
import { writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const require = createRequire(import.meta.url);
const basePath = (process.env.BASE_PATH ?? '/silicon-portfolio').replace(/\/+$/, '');
if (basePath && !/^\/[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*$/.test(basePath)) {
  throw new Error('BASE_PATH must be empty or a URL path such as /silicon-portfolio.');
}

// Explicit empty values also prevent Next from loading connected settings from
// local .env files. No database/API credentials are needed for this public demo.
const env = {
  ...process.env,
  GITHUB_PAGES: 'true',
  BASE_PATH: basePath,
  NEXT_TELEMETRY_DISABLED: '1',
  NEXT_PUBLIC_DATA_MODE: 'demo',
  NEXT_PUBLIC_API_URL: '',
  NEXT_PUBLIC_SUPABASE_URL: '',
  NEXT_PUBLIC_SUPABASE_ANON_KEY: '',
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: '',
  SUPABASE_URL: '',
  SUPABASE_ANON_KEY: '',
  SUPABASE_PUBLISHABLE_KEY: '',
  SUPABASE_SERVICE_ROLE_KEY: '',
  API_URL: '',
};

const result = spawnSync(process.execPath, [require.resolve('next/dist/bin/next'), 'build', 'apps/web'], {
  cwd: root,
  env,
  stdio: 'inherit',
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

await writeFile(resolve(root, 'apps/web/out/.nojekyll'), '');
console.log(`GitHub Pages demo exported to apps/web/out at ${basePath || '/'}.`);
