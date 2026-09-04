"use client";
import MissionMap from "./MissionMap";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import {
  AlertTriangle,
  ChevronDown,
  Ship,
  Snowflake,
  Wind,
  Waves,
  Clock3,
} from "lucide-react";

import type { ForecastResponse } from "./types";

import {
  routes,
  timeOptions,
  icebergTimeline,
  getIcebergMapPosition,
} from "./constants";

import MissionHeader from "./components/MissionHeader";
import MissionControls from "./components/MissionControls";
import MissionTimeline from "./components/MissionTimeline";
import EnvironmentPanel from "./components/EnvironmentPanel";
import IcebergPanel from "./components/IcebergPanel";
import RouteAnalysis from "./components/RouteAnalysis";
import MissionLegend from "./components/MissionLegend";
import { useMissionPlan } from "./hooks/useMissionPlan";

export default function Home() {
  const [selectedHour, setSelectedHour] = useState(0);
  const forecastFetched = useRef(false);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const { missionPlan, missionLoading, missionError, calculateRoutes } =
    useMissionPlan();

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

  const liveForecast = forecast?.forecast;
  const liveEnsemble = forecast?.ensemble;

  const handleCalculateRoutes = async () => {
    await calculateRoutes({
      start: {
        latitude: -63.3,
        longitude: -47.3,
      },
      destination: {
        latitude: -63.0,
        longitude: -46.5,
      },
      vessel_speed_knots: 10,
      icebergs: [
        {
          iceberg_id: "d29c",
          latitude: -63.314,
          longitude: -47.283,
        },
      ],
      sea_ice: [],
    });
  };

  return (
    <main className="min-h-screen bg-[#f3f4f1] text-[#172126]">
      <MissionHeader />

      {/* MAIN */}
      <div className="grid grid-cols-[260px_1fr_300px] h-[calc(100vh-56px)]">
        <MissionControls
          onCalculateRoutes={handleCalculateRoutes}
          loading={missionLoading}
          error={missionError}
          recommendedProfile={missionPlan?.recommended_profile}
        />

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
            currentPosition={{
              latitude: -63.314,
              longitude: -47.283,
            }}
            vesselPosition={{
              latitude: -63.3,
              longitude: -47.3,
            }}
            destinationPosition={{
              latitude: -63.0,
              longitude: -46.5,
            }}
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
            routes={missionPlan?.routes}
            recommendedProfile={missionPlan?.recommended_profile}
          />

          <MissionTimeline
            selectedHour={selectedHour}
            onSelectHour={setSelectedHour}
          />

          <MissionLegend className="absolute bottom-5 left-6" />
        </section>

        {/* RIGHT PANEL */}
        <aside className="border-l border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
          <EnvironmentPanel
            seaIce={environmentState.seaIce}
            wind={environmentState.wind}
            current={environmentState.current}
            environmentType={environmentType}
            selectedHour={selectedHour}
          />

          <IcebergPanel
            selectedHour={selectedHour}
            icebergState={icebergState}
            forecast={forecast}
            cpaKm={
              missionPlan?.routes[missionPlan.recommended_profile]?.evaluation
                .min_iceberg_separation_km
            }
          />

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

          <RouteAnalysis
            routes={
              missionPlan
                ? ["safest", "balanced", "fuel"].map((profile) => {
                    const route = missionPlan.routes[profile];
                    const evaluation = route?.evaluation;

                    return {
                      name:
                        profile === "fuel"
                          ? "Fuel optimized"
                          : profile.charAt(0).toUpperCase() + profile.slice(1),

                      distance: evaluation
                        ? `${evaluation.distance_km.toFixed(1)} km`
                        : "—",

                      eta: evaluation
                        ? `${Math.floor(evaluation.estimated_hours)}h ${Math.round(
                            (evaluation.estimated_hours % 1) * 60,
                          )}m`
                        : "—",

                      risk: evaluation
                        ? evaluation.risk_level
                            .replaceAll("_", " ")
                            .toUpperCase()
                        : "—",

                      cpa:
                        evaluation?.min_iceberg_separation_km != null
                          ? `${evaluation.min_iceberg_separation_km.toFixed(2)} km`
                          : "—",

                      selected: missionPlan.recommended_profile === profile,
                    };
                  })
                : routes
            }
          />
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
