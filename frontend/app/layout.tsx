import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import Nav from "@/components/Nav"
import { TournamentProvider } from "@/context/TournamentContext"
import "./globals.css"

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: "WC 2026 Predictor",
  description: "FIFA World Cup 2026 — ML-powered predictions & Monte Carlo simulation",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full relative">

        {/* Stadium atmosphere blobs — subtle, above the body gradient */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
          {/* Top-centre blue stadium floodlight */}
          <div
            className="absolute -top-48 left-1/2 -translate-x-1/2 w-[900px] h-[600px] rounded-full"
            style={{ background: "radial-gradient(ellipse, rgba(37,99,235,0.1) 0%, transparent 65%)" }}
          />
          {/* Bottom-left green pitch glow */}
          <div
            className="absolute -bottom-40 left-0 w-[700px] h-[500px] rounded-full"
            style={{ background: "radial-gradient(ellipse, rgba(16,185,129,0.08) 0%, transparent 65%)" }}
          />
          {/* Right gold accent */}
          <div
            className="absolute top-1/3 -right-20 w-[450px] h-[450px] rounded-full"
            style={{ background: "radial-gradient(ellipse, rgba(245,158,11,0.07) 0%, transparent 65%)" }}
          />
        </div>

        <TournamentProvider>
          <div className="relative z-10">
            <Nav />
            <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
          </div>
        </TournamentProvider>

      </body>
    </html>
  )
}
