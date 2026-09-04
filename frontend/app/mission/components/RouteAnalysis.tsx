interface RouteAnalysisProps {
  routes: {
    name: string;
    distance: string;
    eta: string;
    risk: string;
    cpa: string;
    selected: boolean;
  }[];
}

export default function RouteAnalysis({
  routes,
}: RouteAnalysisProps) {
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
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

function RouteResult({
  name,
  distance,
  eta,
  risk,
  cpa,
  selected,
}: {
  name: string;
  distance: string;
  eta: string;
  risk: string;
  cpa: string;
  selected: boolean;
}) {
  return (
    <div className={`px-5 py-4 ${selected ? "bg-[#edf2f3]" : ""}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold">
          {name.toUpperCase()}
        </span>

        {selected && (
          <span className="text-[9px] font-semibold text-[#365e72]">
            RECOMMENDED
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-y-3 mt-4">
        <Data label="DISTANCE" value={distance} />

        <Data label="ETA" value={eta} />

        <Data label="RISK" value={risk} />

        <Data label="CPA" value={cpa} />
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
      <div className="text-[9px] text-[#7a8588]">
        {label}
      </div>

      <div className="mt-1 font-mono text-[11px]">
        {value}
      </div>
    </div>
  );
}