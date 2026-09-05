interface RouteAnalysisProps {
  routes: {
    name: string;
    distance: string;
    eta: string;
    risk: string;
    cpa: string;
    icebergExposure: string;
    seaIceExposure: string;
    overallScore: string;
    selected: boolean;
  }[];
}

export default function RouteAnalysis({ routes }: RouteAnalysisProps) {
  return (
    <>
      <SectionTitle title="ROUTE ANALYSIS" />

      <div className="divide-y divide-[#cdd2cf]">
        {routes.map((route) => (
          <RouteResult key={route.name} {...route} />
        ))}
      </div>
    </>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3">
      <span className="text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
        {title}
      </span>
    </div>
  );
}

function RouteResult({
  name,
  distance,
  eta,
  risk,
  cpa,
  icebergExposure,
  seaIceExposure,
  overallScore,
  selected,
}: {
  name: string;
  distance: string;
  eta: string;
  risk: string;
  cpa: string;
  icebergExposure: string;
  seaIceExposure: string;
  overallScore: string;
  selected: boolean;
}) {
  return (
    <div className={`px-5 py-4 ${selected ? "bg-[#edf2f3]" : ""}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold">
          {name.toUpperCase()}
        </span>

        {selected && (
          <span className="text-[9px] font-semibold tracking-wider text-[#365e72]">
            RECOMMENDED
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3">
        <Data label="DISTANCE" value={distance} />
        <Data label="ETA" value={eta} />

        <Data label="RISK" value={risk} />
        <Data label="CPA" value={cpa} />

        <Data label="ICEBERG EXP." value={icebergExposure} />
        <Data label="SEA ICE EXP." value={seaIceExposure} />

        <Data label="OVERALL SCORE" value={overallScore} />
      </div>
    </div>
  );
}

function Data({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-[8px] font-medium tracking-[0.14em] text-[#7a8587]">
        {label}
      </div>

      <div className="mt-1 font-mono text-[11px] text-[#263337]">
        {value}
      </div>
    </div>
  );
}