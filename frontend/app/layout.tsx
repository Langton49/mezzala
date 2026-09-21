import "./globals.css";
import { Space_Grotesk } from "next/font/google";
import { DashboardProvider } from "@/context/DashboardContext";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export default function RootLayout({children}: {children: React.ReactNode}){
  return (
    <html lang="en" className={display.variable}>
      <body>
        <DashboardProvider>
          {children}
        </DashboardProvider>
      </body>
    </html>
  )
}
