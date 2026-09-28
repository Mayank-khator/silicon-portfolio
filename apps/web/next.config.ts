import type { NextConfig } from 'next';

// A normal build is served at /. The Pages build opts into its repository path.
const basePath = process.env.GITHUB_PAGES === 'true'
  ? (process.env.BASE_PATH ?? '/silicon-portfolio').replace(/\/+$/, '')
  : '';

const config: NextConfig = {
  output: 'export',
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
};
export default config;
