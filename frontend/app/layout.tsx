import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
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
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-white text-gray-900 dark:bg-black dark:text-gray-100">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-black/10 bg-white/90 px-4 py-3 backdrop-blur dark:border-white/10 dark:bg-black/90">
          <Link href="/" className="text-sm font-bold">
            올림픽공원 공연 추천
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
      </body>
    </html>
  );
}
