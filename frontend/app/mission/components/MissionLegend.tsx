interface MissionLegendProps {
  className?: string;
}

export default function MissionLegend({
  className = "",
}: MissionLegendProps) {
  return (
    <div
      className={`flex items-center gap-5 text-[10px] text-[#59666a] ${className}`}
    >
      <Legend type="line" label="Recommended route" />

      <Legend type="dash" label="Alternative route" />

      <Legend type="circle" label="Iceberg" />

      <Legend type="box" label="Vessel" />
    </div>
  );
}

function Legend({
  type,
  label,
}: {
  type: "line" | "dash" | "circle" | "box";
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {type === "line" && (
        <span className="w-5 h-0.5 bg-[#365e72]" />
      )}

      {type === "dash" && (
        <span className="w-5 border-t border-dashed border-[#879397]" />
      )}

      {type === "circle" && (
        <span className="w-3 h-3 rounded-full border border-[#a84d43]" />
      )}

      {type === "box" && (
        <span className="w-3 h-3 border border-[#365e72]" />
      )}

      {label}
    </div>
  );
}