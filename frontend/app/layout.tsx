import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "올림픽공원 공연 추천",
  description: "올림픽공원 공연을 취향·날짜에 맞춰 추천합니다.",
  icons: {
    apple: "/icons/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#237034",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-surface/90 px-4 py-3 backdrop-blur">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-md bg-white shadow-[inset_0_0_0_1px_rgba(0,0,0,0.06)]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/olympic-park-mark.png" alt="" width={28} height={28} className="h-6 w-6 object-contain" />
            </span>
            <span className="text-sm font-bold tracking-tight">올림픽공원 공연 추천</span>
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/" className="hover:underline">
              홈
            </Link>
          </nav>
        </header>
        <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-4">
          {children}
        </main>
        <footer className="border-t border-line px-4 py-3 text-center text-xs text-muted">
          본 서비스는 한국체육산업개발 공공데이터를 활용합니다.
        </footer>
        <Script id="sw-register" strategy="afterInteractive">
          {`if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js').catch(function () {}); }`}
        </Script>
      </body>
    </html>
  );
}
