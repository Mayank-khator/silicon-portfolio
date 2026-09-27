import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Silicon Portfolio | NPI Command Center', description: 'Semiconductor new product introduction portfolio, capacity and time management. Synthetic management demo.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
