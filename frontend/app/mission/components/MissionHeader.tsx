export default function MissionHeader() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-[#cdd2cf] bg-[#fafaf8] px-6">
      {/* LEFT */}
      <div className="flex items-center gap-4">
        <div className="text-[13px] font-semibold tracking-[0.16em] text-[#172126]">
          ANTARA
        </div>

        <div className="h-4 w-px bg-[#cdd2cf]" />

        <div className="text-[11px] text-[#687277]">
          Mission Planning
        </div>

        <div className="h-4 w-px bg-[#cdd2cf]" />

        <div className="font-[family-name:var(--font-mono)] text-[9px] tracking-[0.08em] text-[#365e72]">
          VALIDATION SCENARIO · 21 JUL 2023
        </div>
      </div>

      {/* RIGHT */}
      <div className="flex items-center gap-6 text-[11px] text-[#687277]">
        <span>04 SEP 2026</span>

        <span className="font-[family-name:var(--font-mono)] text-[10px]">
          10:42 UTC
        </span>

        <span className="flex items-center gap-2 text-[#426d5a]">
          <span className="h-2 w-2 rounded-full bg-[#426d5a]" />
          DATA AVAILABLE
        </span>
      </div>
    </header>
  );
}