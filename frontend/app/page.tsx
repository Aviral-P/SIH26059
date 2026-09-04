"use client";

import AntarcticGlobe from "@/components/landing/AntarcticGlobe";
import { ArrowRight, ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080b0d] text-[#edf1f2]">
      {/* Globe */}
      <AntarcticGlobe />

      {/* Very subtle vignette */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_25%,rgba(8,11,13,0.58)_78%,#080b0d_100%)]" />

      {/* Top navigation */}
      <header className="absolute left-0 right-0 top-0 z-20 flex items-center justify-between px-8 py-7 md:px-12">
        <div className="flex items-center gap-3">
          <div className="h-2.5 w-2.5 rounded-full bg-[#d9e2e4]" />

          <span className="font-mono text-[11px] tracking-[0.22em] text-[#c4ced1]">
            ANTARCTIC NAVIGATION INTELLIGENCE
          </span>
        </div>

        <div className="font-mono text-[10px] tracking-[0.18em] text-[#7f8b8f]">
          POLAR OPERATIONS SYSTEM
        </div>
      </header>

      {/* Main title */}
      <section className="absolute left-8 top-1/2 z-20 max-w-xl -translate-y-1/2 md:left-12">
        <div className="mb-6 flex items-center gap-3">
          <div className="h-px w-10 bg-[#aeb9bc]" />

          <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[#9da9ad]">
            Mission Intelligence Platform
          </span>
        </div>

        <h1 className="text-5xl font-medium leading-[0.95] tracking-[-0.045em] text-[#f2f4f4] md:text-7xl">
          Navigate
          <br />
          the Antarctic
          <br />
          <span className="text-[#9eaaad]">with foresight.</span>
        </h1>

        <p className="mt-7 max-w-md text-sm leading-7 text-[#9ca7aa] md:text-base">
          Observe sea ice and iceberg movement, forecast environmental
          conditions, assess navigation risk, and compute safer mission routes.
        </p>

        <button
          onClick={() => router.push("/mission")}
          className="group mt-9 flex items-center gap-4 border border-[#899497] bg-[#e7ecec] px-6 py-4 text-xs font-medium tracking-[0.16em] text-[#101416] transition hover:bg-white"
        >
          ENTER MISSION CONTROL
          <ArrowRight
            size={16}
            strokeWidth={1.5}
            className="transition-transform group-hover:translate-x-1"
          />
        </button>
      </section>

      {/* Bottom system information */}
      <div className="absolute bottom-8 left-8 right-8 z-20 flex items-end justify-between md:left-12 md:right-12">
        <div className="flex gap-8 font-mono text-[9px] uppercase tracking-[0.16em] text-[#687579]">
          <div>
            <div className="mb-1 text-[#a4afb2]">Region</div>
            <div>Antarctica</div>
          </div>

          <div>
            <div className="mb-1 text-[#a4afb2]">Focus</div>
            <div>Navigation Risk</div>
          </div>

          <div className="hidden md:block">
            <div className="mb-1 text-[#a4afb2]">Data</div>
            <div>Satellite · Ocean · Ice</div>
          </div>
        </div>

        <div className="hidden items-center gap-2 font-mono text-[9px] tracking-[0.16em] text-[#687579] md:flex">
          EXPLORE
          <ChevronDown size={13} />
        </div>
      </div>
    </main>
  );
}
