"use client";

import AntarcticGlobe from "@/components/landing/AntarcticGlobe";
import { useRouter } from "next/navigation";
import { Archivo, Space_Mono } from "next/font/google";

const sans = Archivo({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const mono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-mono",
});

const APPROACH = [
  {
    n: "01",
    label: "SATELLITE ICE OBSERVATIONS",
    detail: "SAR · PASSIVE MICROWAVE · SEA-ICE RECORDS",
  },
  {
    n: "02",
    label: "OCEAN & ATMOSPHERIC CONDITIONS",
    detail: "HYCOM CURRENTS · ERA5 WIND AND WEATHER",
  },
  {
    n: "03",
    label: "ICEBERG MOVEMENT RECORDS",
    detail: "HISTORICAL OBSERVATIONS · DRIFT TRAJECTORIES",
  },
  {
    n: "04",
    label: "FORECAST & NAVIGATION INTELLIGENCE",
    detail: "DRIFT PREDICTION · UNCERTAINTY · ROUTE RISK",
  },
];

const CAPABILITIES = [
  ["01", "ENVIRONMENTAL OBSERVATION", "SEA ICE · WIND · OCEAN CURRENTS"],
  ["02", "ICEBERG INTELLIGENCE", "DETECTION · TRACKING · MOVEMENT"],
  ["03", "DRIFT FORECASTING", "TRAJECTORY · ENSEMBLE · UNCERTAINTY"],
  ["04", "NAVIGATION RISK", "EXPOSURE · SEPARATION · HAZARD ZONES"],
  ["05", "ROUTE OPTIMIZATION", "SAFETY · DISTANCE · FUEL TRADE-OFFS"],
];

export default function Home() {
  const router = useRouter();

  return (
    <main
      className={`${sans.variable} ${mono.variable} h-screen overflow-hidden bg-[#fafaf8] text-[#172126] font-[family-name:var(--font-sans)] lg:flex`}
    >
      {/* =========================================================
          LEFT PANEL
         ========================================================= */}
      <section className="h-full overflow-y-auto border-r border-[#cdd2cf] bg-[#fafaf8] lg:w-[40%]">
        <div className="min-h-full px-6 py-7 md:px-8 md:py-9">

          {/* PROJECT IDENTITY */}
          <div className="border-b border-[#cdd2cf] pb-5">
            <div className="font-[family-name:var(--font-mono)] text-[9px] uppercase tracking-[0.22em] text-[#687277]">
              PROJECT
            </div>

            <div className="mt-2 text-2xl font-semibold tracking-[0.08em] text-[#172126]">
              ANTARA
            </div>

            <div className="mt-1 max-w-[380px] text-[10px] leading-4 text-[#687277]">
              Antarctic Analytics for Risk-aware Adaptive Navigation
            </div>
          </div>

          {/* MISSION BRIEF */}
          <section className="pt-8">
            <div className="font-[family-name:var(--font-mono)] text-[9px] uppercase tracking-[0.18em] text-[#8b2e23]">
              MISSION BRIEF
            </div>

            <h1 className="mt-5 max-w-[560px] text-[clamp(2.4rem,4vw,4.2rem)] font-semibold leading-[0.98] tracking-[-0.045em] text-[#172126]">
              Route through moving ice with days of warning, not hours.
            </h1>

            <p className="mt-6 max-w-[560px] text-[13px] leading-6 text-[#59666a]">
              Satellite observations, ocean and atmospheric conditions, and
              historical iceberg movement records combined into navigation
              intelligence for vessels operating in the Southern Ocean.
            </p>

            {/* ENTER MISSION CONTROL */}
            <div className="mt-8">
              <button
                type="button"
                onClick={() => router.push("/mission")}
                className="group flex w-full items-center justify-between border border-[#172126] bg-[#172126] px-5 py-3.5 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-[#fafaf8] transition-colors hover:bg-[#2b383d]"
              >
                <span>ENTER MISSION CONTROL</span>

                <span className="font-[family-name:var(--font-mono)] text-sm transition-transform duration-200 group-hover:translate-x-1">
                  →
                </span>
              </button>
            </div>

            <div className="mt-3 font-[family-name:var(--font-mono)] text-[8px] uppercase tracking-[0.14em] text-[#8a9496]">
              OBSERVE / PREDICT / ASSESS / NAVIGATE
            </div>
          </section>

          {/* SYSTEM APPROACH */}
          <section className="mt-12">
            <div className="flex items-center justify-between border-b border-[#cdd2cf] pb-2">
              <span className="font-[family-name:var(--font-mono)] text-[9px] font-bold uppercase tracking-[0.17em] text-[#59666a]">
                SYSTEM APPROACH
              </span>

              <span className="font-[family-name:var(--font-mono)] text-[8px] uppercase tracking-[0.1em] text-[#9aa3a5]">
                DATA PIPELINE
              </span>
            </div>

            <div className="divide-y divide-[#d5dad8]">
              {APPROACH.map((item) => (
                <div
                  key={item.n}
                  className="grid grid-cols-[34px_1fr] gap-3 py-4"
                >
                  <span className="font-[family-name:var(--font-mono)] text-[10px] font-bold text-[#8b2e23]">
                    {item.n}
                  </span>

                  <div>
                    <div className="text-[11px] font-semibold tracking-[0.03em] text-[#263337]">
                      {item.label}
                    </div>

                    <div className="mt-1 font-[family-name:var(--font-mono)] text-[8px] leading-4 tracking-[0.03em] text-[#7a8588]">
                      {item.detail}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* MISSION CAPABILITIES */}
          <section className="mt-10">
            <div className="border-b border-[#cdd2cf] pb-2">
              <span className="font-[family-name:var(--font-mono)] text-[9px] font-bold uppercase tracking-[0.17em] text-[#59666a]">
                MISSION CAPABILITIES
              </span>
            </div>

            <div className="divide-y divide-[#d5dad8]">
              {CAPABILITIES.map(([number, title, detail]) => (
                <div
                  key={number}
                  className="grid grid-cols-[34px_1fr] gap-3 py-3.5"
                >
                  <span className="font-[family-name:var(--font-mono)] text-[10px] font-bold text-[#8b2e23]">
                    {number}
                  </span>

                  <div>
                    <div className="text-[11px] font-semibold tracking-[0.03em] text-[#263337]">
                      {title}
                    </div>

                    <div className="mt-0.5 font-[family-name:var(--font-mono)] text-[8px] leading-4 tracking-[0.02em] text-[#7a8588]">
                      {detail}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* PROJECT REFERENCE */}
          <div className="mt-10 border-t border-[#cdd2cf] pt-4">
            <div className="flex items-center justify-between">
              <span className="font-[family-name:var(--font-mono)] text-[8px] uppercase tracking-[0.14em] text-[#8a9496]">
                ANTARA
              </span>

              <span className="font-[family-name:var(--font-mono)] text-[8px] uppercase tracking-[0.14em] text-[#8a9496]">
                SIH26059
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================
          RIGHT PANEL — INTERACTIVE EARTH
         ========================================================= */}
      <section className="relative hidden h-full overflow-hidden bg-black lg:block lg:w-[60%]">
        <AntarcticGlobe />
      </section>
    </main>
  );
}