import { Snowflake, Wind, Waves } from "lucide-react";
import type { ReactNode } from "react";

interface EnvironmentPanelProps {
  seaIce: string;
  wind: string;
  current: string;
  environmentType: string;
  selectedHour: number;
}

export default function EnvironmentPanel({
  seaIce,
  wind,
  current,
  environmentType,
  selectedHour,
}: EnvironmentPanelProps) {
  return (
    <>
      <SectionTitle title="ENVIRONMENT" />

      <div className="px-5 py-4 space-y-4">
        <EnvironmentRow
          icon={<Snowflake size={15} />}
          label="SEA ICE"
          value={seaIce}
        />

        <EnvironmentRow
          icon={<Wind size={15} />}
          label="WIND"
          value={wind}
        />

        <EnvironmentRow
          icon={<Waves size={15} />}
          label="OCEAN CURRENT"
          value={current}
        />

        <div className="border-t border-[#d7dcda] pt-3">
          <div className="flex items-center justify-between">
            <span className="text-[9px] tracking-[0.14em] text-[#7a8588]">
              ENVIRONMENT STATE
            </span>

            <span
              className={`font-mono text-[9px] ${
                selectedHour > 0
                  ? "text-[#365e72]"
                  : "text-[#426d5a]"
              }`}
            >
              {environmentType}
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

function EnvironmentRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-[#647176]">
        {icon}

        <span className="text-[10px] tracking-wider">
          {label}
        </span>
      </div>

      <span
        className={`font-mono text-[11px] ${
          value === "FORECAST" ? "text-[#365e72]" : ""
        }`}
      >
        {value}
      </span>
    </div>
  );
}