import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { CallProvider } from "@/lib/call";
import { NavBar } from "@/components/NavBar";
import { InstallPrompt } from "@/components/InstallPrompt";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Playhub — Game Platform",
  description: "Upload and play games. Follow creators. Build together.",
  applicationName: "Playhub",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "Playhub" },
  icons: {
    icon: "/icon-192.png",
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#6366f1",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-neutral-950 text-neutral-100">
        <AuthProvider>
          <CallProvider>
            <NavBar />
            <main className="flex-1 w-full max-w-2xl lg:max-w-4xl mx-auto px-4 py-6">
              {children}
            </main>
            <InstallPrompt />
          </CallProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
