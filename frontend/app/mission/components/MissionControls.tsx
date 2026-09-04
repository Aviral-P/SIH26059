import { ChevronDown, Ship } from "lucide-react";

interface MissionControlsProps {
  onCalculateRoutes?: () => void;
  loading?: boolean;
  error?: string | null;
  recommendedProfile?: string;
}

export default function MissionControls({
  onCalculateRoutes,
  loading = false,
  error = null,
  recommendedProfile,
}: MissionControlsProps) {
  return (
    <aside className="border-r border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
      <SectionTitle title="MISSION" />

      <div className="px-5 py-4 space-y-5">
        <CoordinateField
          label="ORIGIN"
          value="63°18.0′ S   47°18.0′ W"
        />

        <CoordinateField
          label="DESTINATION"
          value="63°00.0′ S   46°30.0′ W"
        />

        <div>
          <label className="label">VESSEL</label>

          <button className="select-button">
            <span className="flex items-center gap-2">
              <Ship size={14} />
              POLAR RESEARCH VESSEL
            </span>

            <ChevronDown size={13} />
          </button>
        </div>

        <div>
          <label className="label">CRUISE SPEED</label>

          <div className="field">10.0 knots</div>
        </div>
      </div>

      <SectionTitle title="ROUTING" />

      <div className="px-5 py-4">
        <div className="space-y-2">
          <RouteOption
            name="Safest"
            description="Minimize hazard exposure"
            active={recommendedProfile === "safest"}
          />

          <RouteOption
            name="Balanced"
            description="Risk / distance trade-off"
            active={recommendedProfile === "balanced"}
          />

          <RouteOption
            name="Fuel optimized"
            description="Minimize route distance"
            active={recommendedProfile === "fuel"}
          />
        </div>

        <button
          className="calculate-button disabled:opacity-50"
          onClick={onCalculateRoutes}
          disabled={loading}
        >
          {loading ? "CALCULATING..." : "CALCULATE ROUTES"}
        </button>

        {error && (
          <div className="mt-2 border border-[#d7b9b5] bg-[#f7eeee] px-3 py-2 text-[9px] leading-relaxed text-[#a84d43]">
            ROUTE ERROR: {error}
          </div>
        )}
      </div>

      <SectionTitle title="LAYERS" />

      <div className="px-5 py-4 space-y-3">
        <LayerToggle label="Sea ice concentration" active />

        <LayerToggle label="Iceberg tracks" active />

        <LayerToggle label="Forecast trajectories" active />

        <LayerToggle label="Risk zones" active />

        <LayerToggle label="Ocean currents" />
      </div>
    </aside>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

function CoordinateField({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>

      <div className="field font-mono text-[11px]">
        {value}
      </div>
    </div>
  );
}

function RouteOption({
  name,
  description,
  active = false,
}: {
  name: string;
  description: string;
  active?: boolean;
}) {
  return (
    <div
      className={`border px-3 py-3 ${
        active
          ? "border-[#365e72] bg-[#edf2f3]"
          : "border-[#d5d9d7]"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`h-3 w-3 rounded-full border ${
            active
              ? "border-[#365e72] bg-[#365e72]"
              : "border-[#8c9698]"
          }`}
        />

        <span className="text-[11px] font-medium">
          {name}
        </span>
      </div>

      <p className="ml-5 mt-1 text-[9px] text-[#748084]">
        {description}
      </p>
    </div>
  );
}

function LayerToggle({
  label,
  active,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-[10px]">
      <span className="text-[#58656a]">{label}</span>

      <span
        className={`h-3 w-3 border ${
          active
            ? "border-[#365e72] bg-[#365e72]"
            : "border-[#aeb6b5]"
        }`}
      />
    </div>
  );
}