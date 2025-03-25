"use client";

import { Inter } from "next/font/google";
import "./globals.css";
import dynamic from "next/dynamic";
import { WebSocketProvider } from "@/components/WebSocketProvider";
import ToastContainer from "@/components/ui/ToastContainer";

const inter = Inter({ subsets: ["latin"] });

const AuthProvider = dynamic(
  () =>
    import("@/components/auth/AuthProvider").then((mod) => mod.AuthProvider),
  { ssr: false }
);

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>Skyflo.ai | AI Agent for Cloud Native</title>
      </head>
      <body className={`${inter.className} bg-dark text-gray-200`}>
        <WebSocketProvider>
          <AuthProvider>{children}</AuthProvider>
        </WebSocketProvider>
        <ToastContainer />
      </body>
    </html>
  );
}
