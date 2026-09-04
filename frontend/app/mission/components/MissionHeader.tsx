export default function MissionHeader() {
  return (
    <header className="h-14 border-b border-[#cdd2cf] bg-[#fafaf8] flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div className="text-[13px] font-semibold tracking-[0.16em]">
          ANTARCTIC NAVIGATION INTELLIGENCE
        </div>

        <div className="h-4 w-px bg-[#cdd2cf]" />

        <div className="text-[11px] text-[#687277]">
          Mission Planning
        </div>

        <div className="h-4 w-px bg-[#cdd2cf]" />

        <div className="text-[9px] font-mono tracking-[0.08em] text-[#365e72]">
          VALIDATION SCENARIO · 21 JUL 2023
        </div>
      </div>

      <div className="flex items-center gap-6 text-[11px] text-[#687277]">
        <span>04 SEP 2026</span>
        <span>10:42 UTC</span>

        <span className="flex items-center gap-2 text-[#426d5a]">
          <span className="h-2 w-2 rounded-full bg-[#426d5a]" />
          DATA AVAILABLE
        </span>
      </div>
    </header>
  );
}