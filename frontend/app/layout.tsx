import "./globals.css";
import { Suspense } from "react";
import { Space_Grotesk } from "next/font/google";
import { Metadata } from "next";
import { DashboardProvider } from "@/context/DashboardContext";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  icons: {
    icon: "/MiniLogo.png",
  },
};

export default function RootLayout({children}: {children: React.ReactNode}){
  return (
    <html lang="en" className={display.variable}>
      <body>
        {/* DashboardProvider reads the URL via useSearchParams(), which Next.js
            requires a Suspense boundary for on a statically-prerendered page. */}
        <Suspense>
          <DashboardProvider>
            {children}
          </DashboardProvider>
        </Suspense>
      </body>
    </html>
  )
}
