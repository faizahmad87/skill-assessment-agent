import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Skill Assessment Agent',
  description: 'AI-powered skill assessment and personalized learning plans — free for everyone',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
