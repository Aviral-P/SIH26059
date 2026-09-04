"use client";
import MissionMap from "./MissionMap";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import {
  AlertTriangle,
  Anchor,
  ChevronDown,
  Navigation,
  Ship,
  Snowflake,
  Wind,
  Waves,
  Clock3,
} from "lucide-react";

interface ForecastResponse {
  forecast_id: number;
  iceberg_id: string;
  model: string;
  initial_position: {
    latitude: number;
    longitude: number;
  };
  forecast: {
    hours: number;
    latitude: number;
    longitude: number;
    speed_kmh: number;
    heading_deg: number;
  };
  ensemble: {
    members: number;
    center_latitude: number;
    center_longitude: number;
    uncertainty_radius_km: number;
  };
  base_velocity: {
    u_mps: number;
    v_mps: number;
  };
  integration: {
    step_hours: number;
    steps: number;
  };
}

const routes = [
  {
    name: "Safest",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "4.57 km",
    selected: true,
  },
  {
    name: "Balanced",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "4.57 km",
    selected: false,
  },
  {
    name: "Fuel optimized",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "0.00 km",
    selected: false,
  },
];

const timeOptions = [
  { hour: -24, label: "−24h", type: "PAST" },
  { hour: -12, label: "−12h", type: "PAST" },
  { hour: 0, label: "NOW", type: "CURRENT" },
  { hour: 6, label: "+6h", type: "FORECAST" },
  { hour: 12, label: "+12h", type: "FORECAST" },
  { hour: 24, label: "+24h", type: "FORECAST" },
];

const icebergTimeline = {
  [-24]: {
    lat: "63.388 S",
    lon: "47.554 W",
    status: "OBSERVED",
  },
  [-12]: {
    lat: "63.356 S",
    lon: "47.412 W",
    status: "OBSERVED",
  },
  [0]: {
    lat: "63.314 S",
    lon: "47.283 W",
    status: "CURRENT",
  },
  [6]: {
    lat: "63.267 S",
    lon: "47.126 W",
    status: "FORECAST",
  },
  [12]: {
    lat: "63.220 S",
    lon: "46.967 W",
    status: "FORECAST",
  },
  [24]: {
    lat: "63.126 S",
    lon: "46.653 W",
    status: "FORECAST",
  },
} as const;

/*
 * D29C trajectory positions used by the current prototype map.
 *
 * The latitude/longitude values are represented in icebergTimeline.
 * These x/y values are only the visual projection into the current
 * SVG chart and are not geographic coordinates.
 */
function getIcebergMapPosition(hour: number) {
  const positions = {
    [-24]: { x: 360, y: 300 },
    [-12]: { x: 390, y: 280 },
    [0]: { x: 430, y: 255 },
    [6]: { x: 465, y: 235 },
    [12]: { x: 500, y: 215 },
    [24]: { x: 550, y: 185 },
  };

  return positions[hour as keyof typeof positions] ?? positions[0];
}

const icebergTrajectory = [
  { hour: -24, x: 360, y: 300 },
  { hour: -12, x: 390, y: 280 },
  { hour: 0, x: 430, y: 255 },
  { hour: 6, x: 465, y: 235 },
  { hour: 12, x: 500, y: 215 },
  { hour: 24, x: 550, y: 185 },
];

export default function Home() {
  const [selectedHour, setSelectedHour] = useState(0);
  const forecastFetched = useRef(false);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchForecast() {
      if (forecastFetched.current) return;

      forecastFetched.current = true;

      try {
        setForecastLoading(true);

        const response = await fetch("http://localhost:8000/api/v1/forecast", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            iceberg_id: "d29c",
            latitude: -63.314,
            longitude: -47.283,
            timestamp: "2023-07-21T00:00:00",
            forecast_hours: 24,
            validation: true,
          }),
        });

        const data = await response.json();

        setForecast(data);
      } catch (error) {
        console.error("FORECAST ERROR:", error);

        setForecastError(
          error instanceof Error ? error.message : "Forecast request failed",
        );
      } finally {
        setForecastLoading(false);
      }
    }

    fetchForecast();
  }, []);

  const icebergState =
    icebergTimeline[selectedHour as keyof typeof icebergTimeline];

  const icebergMapPosition = getIcebergMapPosition(selectedHour);

  /*
   * Environment values are only shown where we currently have
   * validated historical observations.
   *
   * Future values are intentionally not fabricated. The UI
   * identifies them as FORECAST until the actual environmental
   * forecast fields are connected.
   */
  const environmentState = {
    seaIce: selectedHour <= 0 ? "85.6 %" : "FORECAST",
    wind: selectedHour <= 0 ? "15.20 m/s" : "FORECAST",
    current: selectedHour <= 0 ? "0.28 m/s" : "FORECAST",
  };

  const environmentType = selectedHour > 0 ? "FORECAST" : "OBSERVED";

  const uncertaintySize = selectedHour === 0 ? 58 : selectedHour > 0 ? 76 : 52;
  const liveForecast = forecast?.forecast;
  const liveEnsemble = forecast?.ensemble;

  const forecastMapPosition = liveForecast
    ? {
        x: 550,
        y: 185,
      }
    : null;

  const displayMapPosition =
    selectedHour === 24 && forecastMapPosition
      ? forecastMapPosition
      : icebergMapPosition;

  const displayUncertaintySize = liveEnsemble
    ? Math.max(44, Math.min(110, liveEnsemble.uncertainty_radius_km * 128))
    : uncertaintySize;

  return (
    <main className="min-h-screen bg-[#f3f4f1] text-[#172126]">
      {/* TOP BAR */}
      <header className="h-14 border-b border-[#cdd2cf] bg-[#fafaf8] flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="text-[13px] font-semibold tracking-[0.16em]">
            ANTARCTIC NAVIGATION INTELLIGENCE
          </div>

          <div className="h-4 w-px bg-[#cdd2cf]" />

          <div className="text-[11px] text-[#687277]">Mission Planning</div>
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

      {/* MAIN */}
      <div className="grid grid-cols-[260px_1fr_300px] h-[calc(100vh-56px)]">
        {/* LEFT CONTROL PANEL */}
        <aside className="border-r border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
          <SectionTitle title="MISSION" />

          <div className="px-5 py-4 space-y-5">
            <CoordinateField label="ORIGIN" value="63°18.0′ S   47°18.0′ W" />

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
                active
              />

              <RouteOption
                name="Balanced"
                description="Risk / distance trade-off"
              />

              <RouteOption
                name="Fuel optimized"
                description="Minimize route distance"
              />
            </div>

            <button className="calculate-button">CALCULATE ROUTES</button>
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

        {/* MAP */}
        <section className="relative overflow-hidden bg-[#dce4e3]">
          {/* Geographic-looking background */}

          {/* Header */}
          <div className="pointer-events-none absolute left-6 top-5 z-10">
            <div className="text-[10px] tracking-[0.16em] text-[#657176]">
              NAVIGATION CHART
            </div>

            <div className="mt-1 text-[13px] font-medium">
              ANTARCTIC PENINSULA
            </div>
          </div>

          {/* Scale */}
          <div className="absolute right-6 top-5 z-10 text-[10px] text-[#657176]">
            SCALE 1 : 2,500,000
          </div>

          {/* REAL MAPLIBRE MAP */}
          <MissionMap
            currentPosition={{ latitude: -63.314, longitude: -47.283 }}
            forecastPosition={
              forecast
                ? {
                    latitude: forecast.forecast.latitude,
                    longitude: forecast.forecast.longitude,
                  }
                : undefined
            }
            uncertaintyKm={
              forecast ? forecast.ensemble.uncertainty_radius_km : undefined
            }
          />

          {/* Map overlay — vessel */}
          <div className="pointer-events-none absolute left-[7%] bottom-[15%] z-10">
            <div className="flex items-center justify-center h-9 w-9 bg-[#f7f8f6] border border-[#365e72]">
              <Anchor size={17} className="text-[#365e72]" />
            </div>

            <div className="mt-1 text-[9px] font-semibold tracking-wider">
              VESSEL
            </div>
          </div>

          {/* Map overlay — D29C */}
          <div
            className="pointer-events-none absolute z-10"
            style={{
              left: `${(displayMapPosition.x / 800) * 100}%`,
              top: `${(displayMapPosition.y / 500) * 100}%`,
              transform: "translate(-50%, -50%)",
            }}
          >
            <div className="relative">
              <div
                className="absolute rounded-full border border-[#a84d43]/30"
                style={{
                  width: `${displayUncertaintySize}px`,
                  height: `${displayUncertaintySize}px`,
                  left: "50%",
                  top: "50%",
                  transform: "translate(-50%, -50%)",
                }}
              />

              <div
                className="absolute rounded-full border border-[#a84d43]/15"
                style={{
                  width: `${displayUncertaintySize + 18}px`,
                  height: `${displayUncertaintySize + 18}px`,
                  left: "50%",
                  top: "50%",
                  transform: "translate(-50%, -50%)",
                }}
              />

              <div className="h-12 w-12 rounded-full border-2 border-[#a84d43] bg-[#f4d9d5]/75 flex items-center justify-center">
                <Snowflake size={18} className="text-[#a84d43]" />
              </div>
            </div>

            <div className="mt-2 whitespace-nowrap text-[9px] font-semibold text-[#a84d43] tracking-wider">
              ICEBERG D29C
            </div>

            <div className="mt-1 whitespace-nowrap font-mono text-[8px] text-[#657176]">
              {icebergState.status}
            </div>
          </div>

          {/* +24H forecast marker */}
          {forecast && (
            <div
              className="pointer-events-none absolute z-10"
              style={{
                left: "69%",
                top: "37%",
                transform: "translate(-50%, -50%)",
              }}
            >
              <div className="h-4 w-4 rounded-full border border-[#365e72] bg-[#eef3f4] flex items-center justify-center">
                <div className="h-1.5 w-1.5 rounded-full bg-[#365e72]" />
              </div>

              <div className="mt-2 whitespace-nowrap text-[8px] font-semibold tracking-wider text-[#365e72]">
                +24H FORECAST
              </div>
            </div>
          )}

          {/* destination */}
          <div className="pointer-events-none absolute right-[5%] top-[7%] z-10">
            <div className="h-8 w-8 border border-[#426d5a] bg-[#eef4ef] flex items-center justify-center">
              <Navigation size={15} className="text-[#426d5a]" />
            </div>

            <div className="mt-1 text-[9px] font-semibold text-[#426d5a] tracking-wider">
              DESTINATION
            </div>
          </div>

          {/* TEMPORAL CONTROL */}
          <div className="absolute bottom-14 left-1/2 z-20 w-[min(720px,80%)] -translate-x-1/2">
            <div className="border border-[#aeb7b6] bg-[#f7f8f6]/95 px-5 py-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock3 size={13} className="text-[#59666a]" />

                  <span className="text-[9px] font-semibold tracking-[0.16em] text-[#59666a]">
                    MISSION TIME
                  </span>
                </div>

                <span className="font-mono text-[10px] text-[#59666a]">
                  {selectedHour === 0
                    ? "CURRENT"
                    : selectedHour > 0
                      ? `T + ${selectedHour}H`
                      : `T ${selectedHour}H`}
                </span>
              </div>

              <div className="relative">
                <div className="absolute left-0 right-0 top-1.25 h-px bg-[#aeb7b6]" />

                <div className="relative flex justify-between">
                  {timeOptions.map((option) => (
                    <button
                      key={option.hour}
                      onClick={() => setSelectedHour(option.hour)}
                      className="group flex flex-col items-center"
                    >
                      <span
                        className={`h-2.75 w-2.75 border ${
                          selectedHour === option.hour
                            ? "border-[#365e72] bg-[#365e72]"
                            : "border-[#718084] bg-[#f7f8f6]"
                        }`}
                      />

                      <span
                        className={`mt-2 font-mono text-[9px] ${
                          selectedHour === option.hour
                            ? "font-semibold text-[#365e72]"
                            : "text-[#687579]"
                        }`}
                      >
                        {option.label}
                      </span>

                      <span className="mt-1 text-[7px] tracking-wider text-[#899396]">
                        {option.type}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="absolute bottom-5 left-6 flex items-center gap-5 text-[10px] text-[#59666a]">
            <Legend type="line" label="Recommended route" />

            <Legend type="dash" label="Alternative route" />

            <Legend type="circle" label="Iceberg" />

            <Legend type="box" label="Vessel" />
          </div>
        </section>

        {/* RIGHT PANEL */}
        <aside className="border-l border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
          <SectionTitle title="ENVIRONMENT" />

          <div className="px-5 py-4 space-y-4">
            <EnvironmentRow
              icon={<Snowflake size={15} />}
              label="SEA ICE"
              value={environmentState.seaIce}
            />

            <EnvironmentRow
              icon={<Wind size={15} />}
              label="WIND"
              value={environmentState.wind}
            />

            <EnvironmentRow
              icon={<Waves size={15} />}
              label="OCEAN CURRENT"
              value={environmentState.current}
            />

            {/* Environment temporal state */}
            <div className="border-t border-[#d7dcda] pt-3">
              <div className="flex items-center justify-between">
                <span className="text-[9px] tracking-[0.14em] text-[#7a8588]">
                  ENVIRONMENT STATE
                </span>

                <span
                  className={`font-mono text-[9px] ${
                    selectedHour > 0 ? "text-[#365e72]" : "text-[#426d5a]"
                  }`}
                >
                  {environmentType}
                </span>
              </div>
            </div>
          </div>

          <SectionTitle title="ICEBERG D29C" />

          <div className="px-5 py-4">
            <div className="grid grid-cols-2 gap-y-4">
              <Data
                label="POSITION"
                value={
                  selectedHour === 24 && forecast
                    ? `${Math.abs(forecast.forecast.latitude).toFixed(3)}° S`
                    : icebergState.lat
                }
              />

              <Data
                label="LONGITUDE"
                value={
                  selectedHour === 24 && forecast
                    ? `${Math.abs(forecast.forecast.longitude).toFixed(3)}° W`
                    : icebergState.lon
                }
              />

              <Data
                label="DRIFT SPEED"
                value={
                  forecast
                    ? `${forecast.forecast.speed_kmh.toFixed(2)} km/h`
                    : "—"
                }
              />

              <Data
                label="HEADING"
                value={
                  forecast
                    ? `${forecast.forecast.heading_deg
                        .toFixed(1)
                        .padStart(5, "0")}°`
                    : "—"
                }
              />

              <Data
                label="UNCERTAINTY"
                value={
                  forecast
                    ? `${forecast.ensemble.uncertainty_radius_km.toFixed(2)} km`
                    : "—"
                }
              />

              <Data label="CPA" value="4.57 km" />
            </div>
          </div>

          {/* Forecast state */}
          <div className="border-y border-[#cdd2cf] bg-[#f4f6f5] px-5 py-4">
            <div className="flex items-center justify-between">
              <span className="text-[9px] tracking-[0.15em] text-[#687579]">
                TEMPORAL STATE
              </span>

              <span className="font-mono text-[9px] text-[#365e72]">
                {icebergState.status}
              </span>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3">
              <Data
                label="SELECTED TIME"
                value={
                  selectedHour === 0
                    ? "NOW"
                    : `${selectedHour > 0 ? "+" : ""}${selectedHour}h`
                }
              />

              <Data
                label="DATA TYPE"
                value={selectedHour <= 0 ? "OBSERVED" : "FORECAST"}
              />
            </div>
          </div>

          {/* Hazard */}
          <div className="border-b border-[#cdd2cf] bg-[#f7eeee] px-5 py-4">
            <div className="flex items-center gap-2 text-[#a84d43]">
              <AlertTriangle size={15} />

              <span className="text-[11px] font-semibold tracking-wider">
                ROUTE HAZARD
              </span>
            </div>

            <p className="mt-2 text-[11px] leading-relaxed text-[#5d4a47]">
              Predicted iceberg trajectory enters the operational route
              corridor.
            </p>
          </div>

          <SectionTitle title="ROUTE ANALYSIS" />

          <div className="divide-y divide-[#cdd2cf]">
            {routes.map((route) => (
              <RouteResult key={route.name} {...route} />
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}

/* -------------------------------------------------- */

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

function CoordinateField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="label">{label}</label>

      <div className="field font-mono text-[11px]">{value}</div>
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
        active ? "border-[#365e72] bg-[#edf2f3]" : "border-[#d5d9d7]"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`h-3 w-3 rounded-full border ${
            active ? "border-[#365e72] bg-[#365e72]" : "border-[#8c9698]"
          }`}
        />

        <span className="text-[11px] font-medium">{name}</span>
      </div>

      <p className="ml-5 mt-1 text-[9px] text-[#748084]">{description}</p>
    </div>
  );
}

function LayerToggle({ label, active }: { label: string; active?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[10px]">
      <span className="text-[#58656a]">{label}</span>

      <span
        className={`h-3 w-3 border ${
          active ? "border-[#365e72] bg-[#365e72]" : "border-[#aeb6b5]"
        }`}
      />
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

        <span className="text-[10px] tracking-wider">{label}</span>
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

function Data({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] text-[#7a8588]">{label}</div>

      <div className="mt-1 font-mono text-[11px]">{value}</div>
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
        <span className="text-[11px] font-semibold">{name.toUpperCase()}</span>

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

function Legend({
  type,
  label,
}: {
  type: "line" | "dash" | "circle" | "box";
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {type === "line" && <span className="w-5 h-0.5 bg-[#365e72]" />}

      {type === "dash" && (
        <span className="w-5 border-t border-dashed border-[#879397]" />
      )}

      {type === "circle" && (
        <span className="w-3 h-3 rounded-full border border-[#a84d43]" />
      )}

      {type === "box" && <span className="w-3 h-3 border border-[#365e72]" />}

      {label}
    </div>
  );
}
