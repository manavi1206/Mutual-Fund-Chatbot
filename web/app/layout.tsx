import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'HDFC Mutual Fund FAQ | Groww',
  description: 'Ask factual questions about HDFC Mutual Funds. Get accurate answers from official documents.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

