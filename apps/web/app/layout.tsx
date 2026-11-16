import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title: 'JARVIS — Shaxsiy AI yordamchingiz', description: 'Fikrlaringiz, bilimlaringiz va rejalaringiz — yagona makonda.'};
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="uz-Latn"><body>{children}</body></html>; }
