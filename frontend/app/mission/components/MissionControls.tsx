"use client";

import { ChevronDown, Ship, Crosshair } from "lucide-react";

interface MissionControlsProps {
  origin: {
    latitude: number;
    longitude: number;
  };

  destination: {
    latitude: number;
    longitude: number;
  };

  vesselSpeed: number;

  onOriginChange: (
    position: {
      latitude: number;
      longitude: number;
    },
  ) => void;

  onDestinationChange: (
    position: {
      latitude: number;
      longitude: number;
    },
  ) => void;

  onVesselSpeedChange: (speed: number) => void;

  onCalculateRoutes?: () => void;

  loading?: boolean;
  error?: string | null;
  recommendedProfile?: string;
}

export default function MissionControls({
  origin,
  destination,
  vesselSpeed,
  onOriginChange,
  onDestinationChange,
  onVesselSpeedChange,
  onCalculateRoutes,
  loading = false,
  error = null,
  recommendedProfile,
}: MissionControlsProps) {
  return (
    <aside className="border-r border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
      <SectionTitle title="MISSION" />

      <div className="px-5 py-4 space-y-5">

        {/* ORIGIN */}
        <CoordinateEditor
          label="ORIGIN"
          position={origin}
          onChange={onOriginChange}
        />

        {/* DESTINATION */}
        <CoordinateEditor
          label="DESTINATION"
          position={destination}
          onChange={onDestinationChange}
        />

        {/* VESSEL */}
        <div>
          <label className="label">VESSEL</label>

          <button
            type="button"
            className="select-button"
          >
            <span className="flex items-center gap-2">
              <Ship size={14} />
              POLAR RESEARCH VESSEL
            </span>

            <ChevronDown size={13} />
          </button>
        </div>

        {/* SPEED */}
        <div>
          <label className="label">CRUISE SPEED</label>

          <div className="flex items-center border border-[#d5d9d7] bg-white">
            <input
              type="number"
              min={1}
              max={30}
              step={0.5}
              value={vesselSpeed}
              onChange={(event) =>
                onVesselSpeedChange(
                  Number(event.target.value),
                )
              }
              className="w-full bg-transparent px-3 py-2 font-mono text-[11px] outline-none"
            />

            <span className="pr-3 font-mono text-[9px] text-[#7a8588]">
              KNOTS
            </span>
          </div>
        </div>
      </div>

      {/* ROUTING */}
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

        {/* CALCULATE */}
        <button
          type="button"
          className="mt-4 flex w-full items-center justify-center gap-2 border border-[#365e72] bg-[#365e72] px-3 py-3 text-[10px] font-semibold tracking-[0.12em] text-white transition hover:bg-[#2d5264] disabled:cursor-not-allowed disabled:opacity-50"
          onClick={onCalculateRoutes}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              CALCULATING...
            </>
          ) : (
            <>
              <Crosshair size={13} />
              CALCULATE ROUTES
            </>
          )}
        </button>

        {error && (
          <div className="mt-2 border border-[#d7b9b5] bg-[#f7eeee] px-3 py-2 text-[9px] leading-relaxed text-[#a84d43]">
            ROUTE ERROR: {error}
          </div>
        )}
      </div>

      {/* LAYERS */}
      <SectionTitle title="LAYERS" />

      <div className="px-5 py-4 space-y-3">

        <LayerToggle
          label="Sea ice concentration"
          active
        />

        <LayerToggle
          label="Iceberg tracks"
          active
        />

        <LayerToggle
          label="Forecast trajectories"
          active
        />

        <LayerToggle
          label="Risk zones"
          active
        />

        <LayerToggle
          label="Ocean currents"
        />

      </div>
    </aside>
  );
}

/* ==================================================
   COORDINATE EDITOR
   ================================================== */

function CoordinateEditor({
  label,
  position,
  onChange,
}: {
  label: string;
  position: {
    latitude: number;
    longitude: number;
  };
  onChange: (
    position: {
      latitude: number;
      longitude: number;
    },
  ) => void;
}) {
  return (
    <div>
      <label className="label">{label}</label>

      <div className="grid grid-cols-2 gap-1">

        <div className="border border-[#d5d9d7] bg-white">
          <div className="flex items-center">
            <input
              type="number"
              step="0.001"
              value={position.latitude}
              onChange={(event) =>
                onChange({
                  ...position,
                  latitude: Number(event.target.value),
                })
              }
              className="min-w-0 w-full bg-transparent px-3 py-2 font-mono text-[10px] outline-none"
            />

            <span className="pr-2 font-mono text-[8px] text-[#7a8588]">
              LAT
            </span>
          </div>
        </div>

        <div className="border border-[#d5d9d7] bg-white">
          <div className="flex items-center">
            <input
              type="number"
              step="0.001"
              value={position.longitude}
              onChange={(event) =>
                onChange({
                  ...position,
                  longitude: Number(event.target.value),
                })
              }
              className="min-w-0 w-full bg-transparent px-3 py-2 font-mono text-[10px] outline-none"
            />

            <span className="pr-2 font-mono text-[8px] text-[#7a8588]">
              LON
            </span>
          </div>
        </div>

      </div>

      <div className="mt-1 font-mono text-[8px] tracking-[0.08em] text-[#8a9496]">
        EPSG:4326 · WGS84
      </div>
    </div>
  );
}

/* ==================================================
   SECTION TITLE
   ================================================== */

function SectionTitle({
  title,
}: {
  title: string;
}) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

/* ==================================================
   ROUTE OPTION
   ================================================== */

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
          : "border-[#d5d9d7] bg-white"
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

        {active && (
          <span className="ml-auto font-mono text-[8px] tracking-wider text-[#365e72]">
            SELECTED
          </span>
        )}

      </div>

      <p className="ml-5 mt-1 text-[9px] text-[#748084]">
        {description}
      </p>
    </div>
  );
}

/* ==================================================
   LAYER TOGGLE
   ================================================== */

function LayerToggle({
  label,
  active,
}: {
  label: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-[10px]">

      <span className="text-[#58656a]">
        {label}
      </span>

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