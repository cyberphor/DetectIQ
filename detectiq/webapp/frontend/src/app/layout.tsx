import { Metadata } from 'next';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'DetectIQ',
  description: 'Detection Engineering Workflow Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
