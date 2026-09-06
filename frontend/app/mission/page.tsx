"use client";

import MissionMap from "./MissionMap";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import type { ForecastResponse } from "./types";

import { routes, icebergTimeline } from "./constants";

import MissionHeader from "./components/MissionHeader";
import MissionControls from "./components/MissionControls";
import MissionTimeline from "./components/MissionTimeline";
import EnvironmentPanel from "./components/EnvironmentPanel";
import IcebergPanel from "./components/IcebergPanel";
import RouteAnalysis from "./components/RouteAnalysis";
import MissionLegend from "./components/MissionLegend";

import { useMissionPlan } from "./hooks/useMissionPlan";
import { useSeaIce } from "./hooks/useSeaIce";
import { useIcebergs } from "./useIcebergs";

interface Position {
  latitude: number;
  longitude: number;
}

interface SelectedIceberg {
  iceberg_id: string;
  observed_at: string;
  latitude: number;
  longitude: number;
}

interface MissionIntelligence {
  status: string;
  summary: string;
  assessment: string;
  recommendation: string;
}

function LayerToggle({
  label,
  active,
  onChange,
}: {
  label: string;
  active: boolean;
  onChange: (active: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      onClick={() => onChange(!active)}
      className={`layer-row ${active ? "is-on" : ""}`}
    >
      <span className="layer-label">{label}</span>
      <span className={`layer-switch ${active ? "is-on" : ""}`} aria-hidden="true">
        <span />
      </span>
    </button>
  );
}

export default function Home() {
  /*
   * ==================================================
   * STATE
   * ==================================================
   */

  const [selectedHour, setSelectedHour] = useState(0);
  const [consoleModal, setConsoleModal] = useState<
    "hazards" | "intelligence" | "routes" | "iceberg" | null
  >(null);

  const [missionControlsOpen, setMissionControlsOpen] = useState(false);
  const [layersOpen, setLayersOpen] = useState(false);

  const [mapLayers, setMapLayers] = useState({
    seaIce: true,
    icebergs: true,
    routes: true,
    forecast: true,
    riskZones: true,
  });

  /*
   * Selected iceberg defaults to D29C for the
   * validation scenario, but is fully dynamic.
   */

  const [selectedIcebergId, setSelectedIcebergId] = useState("d29c");

  /*
   * ==================================================
   * MISSION PARAMETERS
   * ==================================================
   */

  const [origin, setOrigin] = useState<Position>({
    latitude: -63.3,
    longitude: -47.3,
  });

  const [destination, setDestination] = useState<Position>({
    latitude: -63.0,
    longitude: -46.5,
  });

  const [vesselSpeed, setVesselSpeed] = useState(10);

  /*
   * ==================================================
   * FORECAST REQUEST GUARD
   * ==================================================
   */

  const forecastRequestInFlight = useRef(false);

  const forecastRequestIcebergId = useRef<string | null>(null);

  /*
   * ==================================================
   * FORECAST STATE
   * ==================================================
   */

  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  const [forecastLoading, setForecastLoading] = useState(false);

  const [forecastError, setForecastError] = useState<string | null>(null);

  const [forecastIcebergId, setForecastIcebergId] = useState<string | null>(
    null,
  );

  /*
   * ==================================================
   * MISSION PLAN
   * ==================================================
   */

  const [missionNotification, setMissionNotification] = useState<{
    type: "HIGH" | "MEDIUM" | "INFO";
    title: string;
    message: string;
  } | null>(null);

  const [missionIntelligence, setMissionIntelligence] =
    useState<MissionIntelligence | null>(null);

  const [missionIntelligenceLoading, setMissionIntelligenceLoading] =
    useState(false);

  const { missionPlan, missionLoading, missionError, calculateRoutes } =
    useMissionPlan();

  /*
   * ==================================================
   * GLOBAL ROUTE HAZARD NOTIFICATION
   * ==================================================
   */

  useEffect(() => {
    if (!missionPlan) return;

    const recommendedEvaluation =
      missionPlan.routes[missionPlan.recommended_profile]?.evaluation;

    const hazards = recommendedEvaluation?.iceberg_hazards ?? [];

    const unselectedHazards = hazards.filter(
      (hazard) =>
        hazard.is_route_hazard && hazard.iceberg_id !== selectedIcebergId,
    );

    if (unselectedHazards.length === 0) {
      setMissionNotification({
        type: "INFO",
        title: "ROUTE ASSESSMENT COMPLETE",
        message: `${missionPlan.recommended_profile
          .replaceAll("_", " ")
          .toUpperCase()} route has no detected unselected iceberg hazard in the operational corridor.`,
      });

      return;
    }

    const highestRisk = unselectedHazards.some(
      (hazard) => hazard.risk_level.toUpperCase() === "HIGH",
    )
      ? "HIGH"
      : "MEDIUM";

    setMissionNotification({
      type: highestRisk,
      title: "ROUTE HAZARD DETECTED",
      message:
        unselectedHazards.length === 1
          ? `Iceberg ${unselectedHazards[0].iceberg_id} is within the operational passage corridor. Reassessment is advised.`
          : `${unselectedHazards.length} unselected icebergs are within the operational passage corridor. Reassessment is advised.`,
    });
  }, [missionPlan, selectedIcebergId]);

  /*
   * ==================================================
   * REAL NSIDC SEA ICE
   * ==================================================
   */

  const {
    cells: seaIceCells,
    loading: seaIceLoading,
    error: seaIceError,
  } = useSeaIce("20230721");

  /*
   * ==================================================
   * REAL ICEBERG OBSERVATIONS
   * ==================================================
   */

  const {
    icebergs,
    loading: icebergsLoading,
    error: icebergsError,
  } = useIcebergs("20230721");

  /*
   * ==================================================
   * SELECTED REAL ICEBERG
   * ==================================================
   */

  const selectedIceberg: SelectedIceberg | undefined = icebergs.find(
    (iceberg) => iceberg.iceberg_id === selectedIcebergId,
  );

  /*
   * ==================================================
   * DYNAMIC FORECAST
   * ==================================================
   */

  useEffect(() => {
    if (icebergsLoading) {
      return;
    }

    if (!selectedIceberg) {
      setForecast(null);
      setForecastIcebergId(null);
      setForecastError(null);
      setForecastLoading(false);
      return;
    }

    const iceberg = selectedIceberg;

    let cancelled = false;

    if (
      forecastRequestInFlight.current &&
      forecastRequestIcebergId.current === iceberg.iceberg_id
    ) {
      return;
    }

    setForecast(null);
    setForecastIcebergId(null);
    setForecastError(null);
    setForecastLoading(true);

    async function fetchForecast() {
      forecastRequestInFlight.current = true;
      forecastRequestIcebergId.current = iceberg.iceberg_id;

      try {
        const response = await fetch("http://localhost:8000/api/v1/forecast", {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            iceberg_id: iceberg.iceberg_id,
            latitude: iceberg.latitude,
            longitude: iceberg.longitude,
            timestamp: iceberg.observed_at,
            forecast_hours: 24,
            validation: true,
          }),
        });

        if (!response.ok) {
          throw new Error(`Forecast request failed (${response.status})`);
        }

        const data: ForecastResponse = await response.json();

        if (cancelled) {
          return;
        }

        setForecast(data);
        setForecastIcebergId(iceberg.iceberg_id);
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error("FORECAST ERROR:", error);

        setForecast(null);
        setForecastIcebergId(null);

        setForecastError(
          error instanceof Error ? error.message : "Forecast request failed",
        );
      } finally {
        forecastRequestInFlight.current = false;
        forecastRequestIcebergId.current = null;

        if (!cancelled) {
          setForecastLoading(false);
        }
      }
    }

    fetchForecast();

    return () => {
      cancelled = true;
    };
  }, [selectedIcebergId, icebergs, icebergsLoading]);

  /*
   * ==================================================
   * ICEBERG TIMELINE
   * ==================================================
   */

  const icebergState =
    icebergTimeline[selectedHour as keyof typeof icebergTimeline];

  /*
   * ==================================================
   * IS CURRENT FORECAST VALID FOR SELECTION?
   * ==================================================
   */

  const hasSelectedIcebergForecast =
    forecast !== null && forecastIcebergId === selectedIcebergId;

  /*
   * ==================================================
   * SELECTED FORECAST TRAJECTORY POINT
   * ==================================================
   */

  const selectedTrajectoryPoint =
    selectedHour > 0 && hasSelectedIcebergForecast && forecast?.trajectory
      ? forecast.trajectory.find((point) => point.hours === selectedHour)
      : undefined;

  /*
   * ==================================================
   * SELECTED ICEBERG POSITION
   * ==================================================
   */

  const selectedIcebergPosition = selectedTrajectoryPoint
    ? {
        latitude: selectedTrajectoryPoint.latitude,
        longitude: selectedTrajectoryPoint.longitude,
      }
    : selectedIceberg
      ? {
          latitude: selectedIceberg.latitude,
          longitude: selectedIceberg.longitude,
        }
      : {
          latitude: -63.314,
          longitude: -47.283,
        };

  /*
   * ==================================================
   * ENVIRONMENT
   * ==================================================
   */

  const selectedEnvironment = selectedTrajectoryPoint?.environment;

  const formatEnvironmentValue = (
    value: number | null | undefined,
    unit: string,
    digits = 2,
  ) => {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return "—";
    }

    return `${value.toFixed(digits)} ${unit}`;
  };

  const environmentState = {
    seaIce:
      selectedHour === 0
        ? "85.6 %"
        : formatEnvironmentValue(
            selectedEnvironment?.sea_ice_percent,
            "%",
            1,
          ),
    wind:
      selectedHour === 0
        ? "15.20 m/s"
        : formatEnvironmentValue(
            selectedEnvironment?.wind_mps,
            "m/s",
            2,
          ),
    current:
      selectedHour === 0
        ? "0.28 m/s"
        : formatEnvironmentValue(
            selectedEnvironment?.current_mps,
            "m/s",
            2,
          ),
  };

  const environmentType =
    selectedHour > 0
      ? selectedEnvironment
        ? "FORECAST • DATA"
        : "FORECAST • UNAVAILABLE"
      : "OBSERVED";

  /*
   * ==================================================
   * ICEBERG SELECTION
   * ==================================================
   */

  const handleIcebergSelect = (icebergId: string) => {
    setSelectedIcebergId(icebergId);

    setSelectedHour(0);
  };

  /*
   * ==================================================
   * ROUTE CALCULATION
   * ==================================================
   */

  const handleCalculateRoutes = async () => {
    if (
      !Number.isFinite(origin.latitude) ||
      !Number.isFinite(origin.longitude) ||
      !Number.isFinite(destination.latitude) ||
      !Number.isFinite(destination.longitude)
    ) {
      return;
    }

    if (
      origin.latitude < -90 ||
      origin.latitude > 90 ||
      destination.latitude < -90 ||
      destination.latitude > 90 ||
      origin.longitude < -180 ||
      origin.longitude > 180 ||
      destination.longitude < -180 ||
      destination.longitude > 180
    ) {
      return;
    }

    if (!Number.isFinite(vesselSpeed) || vesselSpeed <= 0 || vesselSpeed > 30) {
      return;
    }

    /*
     * Selected iceberg forecast position is used for
     * the selected target. All other icebergs retain
     * their observed positions.
     */

    const routeIcebergPosition = selectedTrajectoryPoint
      ? {
          latitude: selectedTrajectoryPoint.latitude,
          longitude: selectedTrajectoryPoint.longitude,
        }
      : selectedIceberg
        ? {
            latitude: selectedIceberg.latitude,
            longitude: selectedIceberg.longitude,
          }
        : {
            latitude: -63.314,
            longitude: -47.283,
          };

    /*
     * Keep this variable because the selected iceberg
     * position is part of the mission context.
     */

    void routeIcebergPosition;

    /*
     * ==================================================
     * CALCULATE ROUTES
     * ==================================================
     */

    const calculatedPlan = await calculateRoutes({
      start: {
        latitude: origin.latitude,
        longitude: origin.longitude,
      },

      destination: {
        latitude: destination.latitude,
        longitude: destination.longitude,
      },

      vessel_speed_knots: vesselSpeed,

      iceberg_date: "20230721",

      icebergs: icebergs.map((iceberg) => ({
        iceberg_id: iceberg.iceberg_id,

        latitude:
          iceberg.iceberg_id === selectedIcebergId && selectedTrajectoryPoint
            ? selectedTrajectoryPoint.latitude
            : iceberg.latitude,

        longitude:
          iceberg.iceberg_id === selectedIcebergId && selectedTrajectoryPoint
            ? selectedTrajectoryPoint.longitude
            : iceberg.longitude,
      })),
    });

    /*
     * ==================================================
     * LOCAL QWEN 3 8B MISSION INTELLIGENCE
     * ==================================================
     */

    if (!calculatedPlan) {
      setMissionIntelligence(null);
      return;
    }

    const recommended =
      calculatedPlan.routes[calculatedPlan.recommended_profile]?.evaluation;

    if (!recommended) {
      setMissionIntelligence(null);
      return;
    }

    const unselectedHazards = recommended.iceberg_hazards.filter(
      (hazard) =>
        hazard.is_route_hazard && hazard.iceberg_id !== selectedIcebergId,
    );

    setMissionIntelligenceLoading(true);

    try {
      const response = await fetch(
        "http://localhost:8000/api/v1/mission/intelligence",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            mission_data: {
              recommended_profile: calculatedPlan.recommended_profile,

              risk_level: recommended.risk_level,

              minimum_separation_km: recommended.min_iceberg_separation_km,

              iceberg_exposure: recommended.iceberg_exposure,

              sea_ice_exposure: recommended.sea_ice_exposure,

              unselected_iceberg_hazards: unselectedHazards.map((hazard) => ({
                iceberg_id: hazard.iceberg_id,

                effective_separation_km: hazard.effective_separation_km,

                risk_level: hazard.risk_level,
              })),
            },
          }),
        },
      );

      if (!response.ok) {
        throw new Error(`Mission intelligence failed: ${response.status}`);
      }

      const intelligence: MissionIntelligence = await response.json();

      setMissionIntelligence(intelligence);
    } catch (error) {
      console.error("MISSION INTELLIGENCE ERROR:", error);

      setMissionIntelligence({
        status: "unavailable",

        summary: "Mission intelligence unavailable.",

        assessment: "Structured route analysis remains available.",

        recommendation: "Use the route assessment and hazard watch.",
      });
    } finally {
      setMissionIntelligenceLoading(false);
    }
  };

  /*
   * ==================================================
   * ROUTE HAZARD INTELLIGENCE
   * ==================================================
   */

  const recommendedEvaluation =
    missionPlan?.routes[missionPlan.recommended_profile]?.evaluation;

  const recommendedHazards = recommendedEvaluation?.iceberg_hazards ?? [];

  const recommendedRisk = recommendedEvaluation?.risk_level
    ?.replaceAll("_", " ")
    .toUpperCase();

  const recommendedCpa = recommendedEvaluation?.min_iceberg_separation_km;

  const hasRouteEvaluation = recommendedEvaluation != null;

  const hazardIsHigh =
    recommendedRisk === "HIGH" ||
    (recommendedCpa != null && recommendedCpa <= 5);

  const hazardIsMedium =
    !hazardIsHigh &&
    (recommendedRisk === "MEDIUM" ||
      (recommendedCpa != null && recommendedCpa <= 15));

  const hazardTitle = !hasRouteEvaluation
    ? "ROUTE STATUS"
    : hazardIsHigh
      ? "ROUTE HAZARD"
      : hazardIsMedium
        ? "ROUTE CAUTION"
        : "ROUTE STATUS";

  const hazardMessage = !hasRouteEvaluation
    ? hasSelectedIcebergForecast
      ? "Forecast available; calculate routes to evaluate corridor exposure."
      : "Route assessment is awaiting a valid forecast or route evaluation."
    : hazardIsHigh
      ? "Predicted iceberg trajectory presents a high-exposure condition along the recommended route."
      : hazardIsMedium
        ? "Recommended route passes through a moderate iceberg exposure zone."
        : "No significant iceberg separation hazard detected on the recommended route.";

  const hazardCpa =
    recommendedCpa != null ? `${recommendedCpa.toFixed(2)} km` : "—";

  const getRouteDecisionBasis = () => {
    if (!missionPlan) {
      return null;
    }

    const recommended =
      missionPlan.routes[missionPlan.recommended_profile]?.evaluation;

    if (!recommended) {
      return null;
    }

    const profile = missionPlan.recommended_profile
      .replaceAll("_", " ")
      .toUpperCase();

    const reasons: string[] = [];

    if (recommended.min_iceberg_separation_km != null) {
      reasons.push(
        `minimum iceberg separation ${recommended.min_iceberg_separation_km.toFixed(2)} km`,
      );
    }

    if (recommended.iceberg_exposure != null) {
      reasons.push(
        `iceberg exposure ${recommended.iceberg_exposure.toFixed(2)}`,
      );
    }

    if (recommended.sea_ice_exposure != null) {
      reasons.push(
        `sea-ice exposure ${recommended.sea_ice_exposure.toFixed(2)}`,
      );
    }

    if (recommended.distance_km != null) {
      reasons.push(`route distance ${recommended.distance_km.toFixed(1)} km`);
    }

    return {
      profile,

      text:
        reasons.length > 0
          ? `${profile} selected using ${reasons.join(", ")}.`
          : `${profile} selected by the route optimization model.`,
    };
  };

  /*
   * ==================================================
   * UI
   * ==================================================
   */

  return (
    <main className="min-h-screen bg-[#f3f4f1] text-[#172126]">
      <MissionHeader />

      <div className="grid grid-cols-[1fr_370px] h-[calc(100vh-56px)]">
        {/* ==================================================
            MAP + SLIDING MISSION / LAYERS DRAWERS
            ================================================== */}

        <section className="relative overflow-hidden bg-[#dce4e3]">
          {!missionControlsOpen && (
            <button
              type="button"
              aria-label="Open mission controls"
              aria-expanded={missionControlsOpen}
              onClick={() => setMissionControlsOpen(true)}
              className="map-edge-tab map-edge-tab-left"
            >
              <span className="tab-glyph">☰</span>
              <span>MISSION</span>
            </button>
          )}

          {!layersOpen && (
            <button
              type="button"
              aria-label="Open map layers"
              aria-expanded={layersOpen}
              onClick={() => setLayersOpen(true)}
              className="map-edge-tab map-edge-tab-right"
            >
              <span>LAYERS</span>
              <span className="tab-glyph">◫</span>
            </button>
          )}

          <div className={`map-drawer map-drawer-left ${missionControlsOpen ? "is-open" : ""}`}>
            <MissionControls
              origin={origin}
              destination={destination}
              vesselSpeed={vesselSpeed}
              onOriginChange={setOrigin}
              onDestinationChange={setDestination}
              onVesselSpeedChange={setVesselSpeed}
              onCalculateRoutes={handleCalculateRoutes}
              loading={missionLoading}
              error={missionError}
              recommendedProfile={missionPlan?.recommended_profile}
              onClose={() => setMissionControlsOpen(false)}
            />
          </div>

          <div className={`map-drawer map-drawer-right ${layersOpen ? "is-open" : ""}`}>
            <div className="layers-panel">
              <div className="layers-panel-head">
                <div>
                  <div className="drawer-eyebrow">NAVIGATION CHART</div>
                  <div className="drawer-title">MAP LAYERS</div>
                </div>
                <button
                  type="button"
                  className="drawer-close"
                  onClick={() => setLayersOpen(false)}
                  aria-label="Close map layers"
                >
                  ×
                </button>
              </div>

              <div className="layers-panel-body">
                <LayerToggle label="SEA ICE CONCENTRATION" active={mapLayers.seaIce} onChange={(active) => setMapLayers((v) => ({ ...v, seaIce: active }))} />
                <LayerToggle label="ICEBERG OBSERVATIONS" active={mapLayers.icebergs} onChange={(active) => setMapLayers((v) => ({ ...v, icebergs: active }))} />
                <LayerToggle label="MISSION ROUTES" active={mapLayers.routes} onChange={(active) => setMapLayers((v) => ({ ...v, routes: active }))} />
                <LayerToggle label="FORECAST TRAJECTORY" active={mapLayers.forecast} onChange={(active) => setMapLayers((v) => ({ ...v, forecast: active }))} />
                <LayerToggle label="RISK ZONES" active={mapLayers.riskZones} onChange={(active) => setMapLayers((v) => ({ ...v, riskZones: active }))} />
              </div>

              <div className="layers-panel-foot">
                <span>CORE REFERENCES</span>
                <b>VESSEL · DESTINATION · TRACKED ICEBERG</b>
              </div>
            </div>
          </div>
          <div className="pointer-events-none absolute left-6 top-5 z-10">
            <div className="text-[10px] tracking-[0.16em] text-[#657176]">
              NAVIGATION CHART
            </div>

            <div className="mt-1 text-[13px] font-medium">
              ANTARCTIC PENINSULA
            </div>
          </div>

          <div className="pointer-events-none absolute right-6 top-5 z-10 text-[10px] text-[#657176]">
            SCALE 1 : 2,500,000
          </div>

          <MissionMap
            currentPosition={selectedIcebergPosition}
            vesselPosition={origin}
            destination={destination}
            trajectoryStartPosition={
              selectedIceberg
                ? {
                    latitude: selectedIceberg.latitude,
                    longitude: selectedIceberg.longitude,
                  }
                : {
                    latitude: -63.314,
                    longitude: -47.283,
                  }
            }
            forecastPosition={
              selectedHour === 24 && hasSelectedIcebergForecast && forecast
                ? {
                    latitude: forecast.forecast.latitude,
                    longitude: forecast.forecast.longitude,
                  }
                : undefined
            }
            uncertaintyKm={
              selectedHour === 24 && hasSelectedIcebergForecast && forecast
                ? forecast.ensemble.uncertainty_radius_km
                : undefined
            }
            routes={missionPlan?.routes}
            recommendedProfile={missionPlan?.recommended_profile}
            riskLevel={recommendedEvaluation?.risk_level}
            riskCpaKm={
              recommendedEvaluation?.min_iceberg_separation_km ?? undefined
            }
            trajectory={
              hasSelectedIcebergForecast ? forecast?.trajectory : undefined
            }
            seaIce={seaIceCells}
            icebergs={icebergs}
            selectedIcebergId={selectedIcebergId}
            layerVisibility={mapLayers}
            onIcebergSelect={handleIcebergSelect}
          />

          <div className="timeline-glass-shell">
            <MissionTimeline
              selectedHour={selectedHour}
              onSelectHour={setSelectedHour}
            />
          </div>

          <MissionLegend className="absolute bottom-5 left-6" />
        </section>

        {/* ==================================================
            RIGHT INTELLIGENCE PANEL
            ================================================== */}

        <aside className="polar-console">
          <div className="polar-console-header">
            <div>
              <div className="console-eyebrow">POLAR OPERATIONS</div>
              <div className="console-heading">MISSION CONSOLE</div>
            </div>
            <div className="console-time">
              {selectedHour === 0 ? "NOW" : `T+${selectedHour}H`}
            </div>
          </div>

          <div className="console-body">
            {/* ENVIRONMENT STRIP */}
            <section className="console-card environment-card">
              <div className="card-head">
                <span>ENVIRONMENT</span>
                <span className="data-state">
                  {environmentType}
                </span>
              </div>

              <div className="metric-strip">
                <div className="metric">
                  <span>SEA ICE</span>
                  <strong>{environmentState.seaIce}</strong>
                </div>
                <div className="metric">
                  <span>WIND</span>
                  <strong>{environmentState.wind}</strong>
                </div>
                <div className="metric">
                  <span>CURRENT</span>
                  <strong>{environmentState.current}</strong>
                </div>
              </div>
            </section>

            {/* TRACKED ICEBERG */}
            <button
              type="button"
              className="console-card iceberg-card"
              onClick={() => setConsoleModal("iceberg")}
            >
              <div className="card-head">
                <span>TRACKED ICEBERG</span>
                <span className="open-label">DETAILS ↗</span>
              </div>

              <div className="iceberg-main">
                <div>
                  <div className="iceberg-id">
                    {selectedIceberg?.iceberg_id?.toUpperCase() ?? "—"}
                  </div>
                  <div className="iceberg-position">
                    {selectedIcebergPosition.latitude.toFixed(3)}° ·{" "}
                    {selectedIcebergPosition.longitude.toFixed(3)}°
                  </div>
                </div>

                <div className={`risk-badge ${
                  hazardIsHigh ? "risk-high" : hazardIsMedium ? "risk-medium" : "risk-low"
                }`}>
                  {recommendedRisk ?? "UNASSESSED"}
                </div>
              </div>

              <div className="iceberg-stats">
                <div>
                  <span>CPA</span>
                  <strong>{hazardCpa}</strong>
                </div>
                <div>
                  <span>TIME</span>
                  <strong>{selectedHour === 0 ? "OBS" : `+${selectedHour}H`}</strong>
                </div>
                <div>
                  <span>STATE</span>
                  <strong>{selectedHour === 0 ? "OBSERVED" : "FORECAST"}</strong>
                </div>
              </div>
            </button>

            {/* ROUTE DECISION */}
            <section className={`console-card route-card ${
              hazardIsHigh ? "route-high" : hazardIsMedium ? "route-medium" : ""
            }`}>
              <div className="card-head">
                <span>ROUTE DECISION</span>
                <span className="data-state">
                  {hasRouteEvaluation ? "ASSESSED" : "PENDING"}
                </span>
              </div>

              {hasRouteEvaluation && recommendedEvaluation ? (
                <>
                  <div className="route-profile-row">
                    <div>
                      <span className="metric-label">RECOMMENDED</span>
                      <strong className="route-profile">
                        {missionPlan?.recommended_profile
                          ?.replaceAll("_", " ")
                          .toUpperCase()}
                      </strong>
                    </div>
                    <div className="route-risk">
                      <span>RISK</span>
                      <strong>{recommendedRisk}</strong>
                    </div>
                  </div>

                  <div className="route-metrics">
                    <div>
                      <span>SEPARATION</span>
                      <strong>{hazardCpa}</strong>
                    </div>
                    <div>
                      <span>DISTANCE</span>
                      <strong>{recommendedEvaluation.distance_km.toFixed(1)} km</strong>
                    </div>
                    <div>
                      <span>ETA</span>
                      <strong>{Math.floor(recommendedEvaluation.estimated_hours)}h</strong>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleCalculateRoutes}
                    disabled={missionLoading}
                    className="reassess-command"
                  >
                    {missionLoading
                      ? selectedHour > 0
                        ? `REASSESSING +${selectedHour}H...`
                        : "CALCULATING..."
                      : selectedHour > 0
                        ? `REASSESS +${selectedHour}H ROUTE`
                        : "RECALCULATE ROUTE"}
                  </button>
                </>
              ) : (
                <div className="empty-route">
                  <span>NO ROUTE ASSESSMENT</span>
                  <button
                    type="button"
                    onClick={handleCalculateRoutes}
                    disabled={missionLoading}
                    className="reassess-command"
                  >
                    {missionLoading ? "CALCULATING..." : "CALCULATE ROUTE"}
                  </button>
                </div>
              )}
            </section>

            {/* HAZARD WATCH */}
            <button
              type="button"
              className="console-card hazard-card"
              onClick={() => setConsoleModal("hazards")}
            >
              <div className="card-head">
                <span>HAZARD WATCH</span>
                <span className={recommendedHazards.some(h => h.is_route_hazard) ? "alert-count" : "data-state"}>
                  {recommendedHazards.filter(h => h.is_route_hazard).length} ACTIVE
                </span>
              </div>

              <div className="hazard-preview">
                {recommendedHazards.filter(h => h.is_route_hazard).slice(0, 2).map((hazard) => (
                  <div className="hazard-row" key={hazard.iceberg_id}>
                    <span className={`hazard-dot ${
                      hazard.risk_level === "HIGH"
                        ? "dot-high"
                        : hazard.risk_level === "MEDIUM"
                          ? "dot-medium"
                          : "dot-low"
                    }`} />
                    <strong>{hazard.iceberg_id.toUpperCase()}</strong>
                    <span>{hazard.effective_separation_km.toFixed(1)} km</span>
                    <span>{hazard.risk_level}</span>
                  </div>
                ))}
                {recommendedHazards.filter(h => h.is_route_hazard).length === 0 && (
                  <div className="clear-hazard">NO ACTIVE ROUTE HAZARDS</div>
                )}
              </div>

              <div className="card-action">OPEN HAZARD BOARD ↗</div>
            </button>

            {/* INTELLIGENCE PREVIEW */}
            <button
              type="button"
              className="console-card intelligence-card"
              onClick={() => setConsoleModal("intelligence")}
            >
              <div className="card-head">
                <span>MISSION INTELLIGENCE</span>
                <span className="qwen-mark">
                  {missionIntelligenceLoading ? "ANALYSING" : "QWEN 3 8B"}
                </span>
              </div>

              <div className="intel-preview">
                {missionIntelligenceLoading
                  ? "Generating operational assessment..."
                  : missionIntelligence?.assessment ??
                    "Calculate a route to generate the operational assessment."}
              </div>

              <div className="card-action">OPEN ASSESSMENT ↗</div>
            </button>

            {/* ROUTE COMPARISON — always visible, compact */}
            <section className="console-card route-compare">
              <div className="card-head">
                <span>ROUTE OPTIONS</span>
                <button
                  type="button"
                  className="open-label"
                  onClick={() => setConsoleModal("routes")}
                >
                  COMPARE ↗
                </button>
              </div>

              <div className="route-option-grid">
                {["safest", "balanced", "fuel_optimized"].map((profile) => {
                  const evaluation = missionPlan?.routes[profile]?.evaluation;
                  const selected = missionPlan?.recommended_profile === profile;

                  return (
                    <button
                      type="button"
                      key={profile}
                      onClick={() => setConsoleModal("routes")}
                      className={`route-option ${selected ? "route-selected" : ""}`}
                    >
                      <span>
                        {profile === "fuel_optimized"
                          ? "FUEL"
                          : profile.toUpperCase()}
                      </span>
                      <strong>
                        {evaluation?.distance_km != null
                          ? `${evaluation.distance_km.toFixed(1)} km`
                          : "—"}
                      </strong>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>
        </aside>
      </div>

      {/* DETAIL MODAL */}
      {consoleModal && (
        <div
          className="console-modal-backdrop"
          onClick={() => setConsoleModal(null)}
        >
          <div
            className="console-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <div className="console-eyebrow">MISSION CONSOLE</div>
                <div className="modal-title">
                  {consoleModal === "hazards"
                    ? "HAZARD BOARD"
                    : consoleModal === "intelligence"
                      ? "OPERATIONAL ASSESSMENT"
                      : consoleModal === "routes"
                        ? "ROUTE COMPARISON"
                        : "ICEBERG TRACK"}
                </div>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setConsoleModal(null)}
              >
                ESC
              </button>
            </div>

            {consoleModal === "hazards" && (
              <div className="modal-content">
                <div className="modal-intro">
                  Recommended corridor hazards at{" "}
                  <strong>{selectedHour === 0 ? "CURRENT" : `+${selectedHour}H`}</strong>.
                </div>
                <div className="modal-hazard-list">
                  {recommendedHazards.filter(h => h.is_route_hazard).map((hazard) => (
                    <div className="modal-hazard" key={hazard.iceberg_id}>
                      <div>
                        <strong>{hazard.iceberg_id.toUpperCase()}</strong>
                        <span>{hazard.risk_level} · EFFECTIVE SEPARATION</span>
                      </div>
                      <strong>{hazard.effective_separation_km.toFixed(2)} km</strong>
                    </div>
                  ))}
                  {recommendedHazards.filter(h => h.is_route_hazard).length === 0 && (
                    <div className="modal-empty">NO ICEBERG WITHIN OPERATIONAL CORRIDOR</div>
                  )}
                </div>
                <button
                  type="button"
                  className="modal-command"
                  onClick={() => {
                    setConsoleModal(null);
                    handleCalculateRoutes();
                  }}
                  disabled={missionLoading}
                >
                  {missionLoading
                    ? "REASSESSING..."
                    : selectedHour > 0
                      ? `REASSESS +${selectedHour}H ROUTE`
                      : "RECALCULATE ROUTE"}
                </button>
              </div>
            )}

            {consoleModal === "intelligence" && (
              <div className="modal-content">
                <div className="intel-block">
                  <span>SUMMARY</span>
                  <p>{missionIntelligence?.summary ?? "No assessment available."}</p>
                </div>
                <div className="intel-block">
                  <span>ASSESSMENT</span>
                  <p>{missionIntelligence?.assessment ?? "No assessment available."}</p>
                </div>
                <div className="intel-recommendation">
                  <span>RECOMMENDATION</span>
                  <p>{missionIntelligence?.recommendation ?? "Review the structured route assessment."}</p>
                </div>
                <div className="decision-basis-modal">
                  <span>DECISION BASIS</span>
                  <p>{getRouteDecisionBasis()?.text ?? "Route assessment pending."}</p>
                </div>
              </div>
            )}

            {consoleModal === "routes" && (
              <div className="modal-content">
                <div className="full-route-list">
                  {["safest", "balanced", "fuel_optimized"].map((profile) => {
                    const evaluation = missionPlan?.routes[profile]?.evaluation;
                    return (
                      <div
                        className={`full-route ${missionPlan?.recommended_profile === profile ? "full-route-selected" : ""}`}
                        key={profile}
                      >
                        <div>
                          <strong>
                            {profile === "fuel_optimized"
                              ? "FUEL OPTIMIZED"
                              : profile.toUpperCase()}
                          </strong>
                          {missionPlan?.recommended_profile === profile && (
                            <span>RECOMMENDED</span>
                          )}
                        </div>
                        <div className="full-route-metrics">
                          <span>CPA <b>{evaluation?.min_iceberg_separation_km != null
                            ? `${evaluation.min_iceberg_separation_km.toFixed(2)} km`
                            : "—"}</b></span>
                          <span>DIST <b>{evaluation ? `${evaluation.distance_km.toFixed(1)} km` : "—"}</b></span>
                          <span>RISK <b>{evaluation?.risk_level?.toUpperCase() ?? "—"}</b></span>
                          <span>SCORE <b>{evaluation ? evaluation.overall_score.toFixed(2) : "—"}</b></span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {consoleModal === "iceberg" && (
              <div className="modal-content">
                <div className="iceberg-modal-hero">
                  <div className="big-iceberg-id">
                    {selectedIceberg?.iceberg_id?.toUpperCase() ?? "—"}
                  </div>
                  <div className="risk-badge modal-risk">
                    {recommendedRisk ?? "UNASSESSED"}
                  </div>
                </div>
                <div className="modal-data-grid">
                  <Data label="LATITUDE" value={`${selectedIcebergPosition.latitude.toFixed(4)}°`} />
                  <Data label="LONGITUDE" value={`${selectedIcebergPosition.longitude.toFixed(4)}°`} />
                  <Data label="SEPARATION" value={hazardCpa} />
                  <Data label="TIME" value={selectedHour === 0 ? "OBSERVED" : `+${selectedHour}H FORECAST`} />
                </div>
                <p className="modal-note">
                  Selected iceberg trajectory is propagated into route reassessment at the selected forecast time.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================
          FORECAST LOADING
          ================================================== */}

      {forecastLoading && (
        <div className="pointer-events-none fixed bottom-3 right-3 z-50 bg-[#172126] px-3 py-2 font-mono text-[9px] tracking-wider text-white">
          FORECASTING {selectedIcebergId.toUpperCase()}
        </div>
      )}

      {/* ==================================================
          FORECAST ERROR
          ================================================== */}

      {forecastError && !forecastLoading && (
        <div className="pointer-events-none fixed bottom-3 right-3 z-50 bg-[#7f3932] px-3 py-2 font-mono text-[9px] tracking-wider text-white">
          FORECAST UNAVAILABLE
        </div>
      )}

      {/* ==================================================
          SEA ICE LOADING
          ================================================== */}

      {seaIceLoading && (
        <div className="pointer-events-none fixed bottom-3 left-1/2 z-50 -translate-x-1/2 bg-[#172126] px-3 py-2 font-mono text-[9px] tracking-wider text-white">
          LOADING SEA ICE...
        </div>
      )}

      {/* ==================================================
          SEA ICE ERROR
          ================================================== */}

      {seaIceError && (
        <div className="pointer-events-none fixed bottom-3 left-1/2 z-50 -translate-x-1/2 bg-[#7f3932] px-3 py-2 font-mono text-[9px] tracking-wider text-white">
          SEA ICE ERROR
        </div>
      )}

      {/* ==================================================
          MISSION INTELLIGENCE NOTIFICATION
          ================================================== */}


      <style jsx global>{`
        /* =========================================================
           POLAR OPERATIONS CONSOLE
           Dense, high-contrast, instrument-like — not a dashboard.
           ========================================================= */

        .mission-drawer-panel {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: #e9edf0;
          color: #1b2a30;
        }

        .mission-drawer-header {
          min-height: 82px;
          flex: 0 0 82px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 18px;
          background: #243c47;
          color: #f4f7f7;
          border-bottom: 3px solid #73939e;
        }

        .mission-drawer-eyebrow {
          font-size: 9px;
          letter-spacing: .17em;
          font-weight: 800;
          color: #a9c0c7;
        }

        .mission-drawer-title {
          margin-top: 5px;
          font-size: 16px;
          line-height: 1;
          font-weight: 800;
          letter-spacing: .06em;
        }

        .mission-drawer-close {
          width: 30px;
          height: 30px;
          display: grid;
          place-items: center;
          border: 1px solid #718d97;
          background: #1c3039;
          color: #f2f6f6;
        }

        .mission-drawer-close:hover { background: #315664; }

        .mission-drawer-body {
          flex: 1;
          min-height: 0;
          padding: 12px;
          overflow-y: auto;
          display: grid;
          align-content: start;
          gap: 9px;
        }

        .mission-control-card {
          border: 1px solid #aebcc2;
          background: #f8faf9;
          box-shadow: 0 1px 0 rgba(25,45,52,.05);
        }

        .mission-card-head {
          min-height: 34px;
          padding: 9px 11px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid #d2dade;
          color: #52666e;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .12em;
        }

        .mission-card-code {
          font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
          color: #66828c;
          letter-spacing: .08em;
        }

        .mission-card-body {
          padding: 11px;
          display: grid;
          gap: 11px;
        }

        .mission-field { display: grid; gap: 5px; }

        .mission-field > label {
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .11em;
          color: #6d7f86;
        }

        .coordinate-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 5px;
        }

        .mission-input-field,
        .mission-static-field {
          min-height: 36px;
          display: flex;
          align-items: center;
          border: 1px solid #bdc9ce;
          background: #ffffff;
        }

        .mission-input-field input {
          width: 100%;
          min-width: 0;
          height: 34px;
          padding: 0 9px;
          border: 0;
          outline: 0;
          background: transparent;
          color: #213940;
          font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
        }

        .mission-input-field span {
          flex: 0 0 auto;
          padding-right: 8px;
          color: #7b8b91;
          font: 800 8px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: .06em;
        }

        .mission-static-field {
          gap: 8px;
          padding: 0 10px;
          color: #36535d;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .05em;
        }

        .route-profile-list { gap: 6px; }

        .mission-route-option {
          min-height: 55px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 0 10px;
          border: 1px solid #c1cdd1;
          background: #f4f7f7;
          color: #4d646c;
        }

        .mission-route-option.is-active {
          border-left: 4px solid #4c7b89;
          padding-left: 7px;
          background: #e5eef0;
          border-color: #7e9ba4;
        }

        .mission-route-option strong {
          display: block;
          font-size: 10px;
          letter-spacing: .08em;
          color: #294650;
        }

        .mission-route-option span:not(.mission-route-state) {
          display: block;
          margin-top: 3px;
          font-size: 8px;
          color: #75858a;
        }

        .mission-route-state {
          flex: 0 0 auto;
          font: 800 8px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
          letter-spacing: .08em;
          color: #63818b;
        }

        .mission-calculate {
          min-height: 42px;
          margin-top: 3px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          border: 1px solid #365e72;
          background: #365e72;
          color: #182b32;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .12em;
          transition: background .16s ease;
        }

        .mission-calculate:hover { background: #2d5264; }
        .mission-calculate:disabled { cursor: not-allowed; opacity: .55; }

        .mission-pulse {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #ffffff;
          animation: missionPulse 1s ease-in-out infinite;
        }

        .mission-error {
          padding: 8px 9px;
          border: 1px solid #d7b9b5;
          background: #f7eeee;
          color: #a84d43;
          font-size: 8px;
          line-height: 1.45;
        }

        @keyframes missionPulse {
          0%, 100% { opacity: .35; transform: scale(.8); }
          50% { opacity: 1; transform: scale(1); }
        }

        .map-edge-tab {
          position: absolute;
          top: 50%;
          z-index: 40;
          width: 34px;
          height: 118px;
          transform: translateY(-50%);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          writing-mode: vertical-rl;
          text-orientation: mixed;
          border: 1px solid #9db1b8;
          background: rgba(239,245,246,.92);
          color: #385763;
          box-shadow: 0 5px 18px rgba(32,52,60,.14);
          backdrop-filter: blur(12px);
          font-size: 9px;
          font-weight: 800;
          letter-spacing: .14em;
          transition: all .18s ease;
        }

        .map-edge-tab:hover,
        .map-edge-tab.is-active {
          background: #294b57;
          color: #f5f8f8;
          border-color: #294b57;
        }

        .map-edge-tab-left { left: 0; border-left: 0; }
        .map-edge-tab-right { right: 0; border-right: 0; }
        .tab-glyph { font-size: 12px; line-height: 1; }

        .map-drawer {
          position: absolute;
          top: 0;
          bottom: 0;
          z-index: 35;
          width: 300px;
          pointer-events: none;
          transition: transform .22s cubic-bezier(.2,.8,.2,1);
        }

        .map-drawer-left { left: 0; transform: translateX(-102%); }
        .map-drawer-right { right: 0; width: 320px; transform: translateX(102%); }
        .map-drawer.is-open { transform: translateX(0); pointer-events: auto; }

        .map-drawer-left > aside {
          height: 100%;
          overflow-y: auto;
          border-right: 1px solid #9eafb5;
          background: #e9edf0;
          box-shadow: 8px 0 24px rgba(32,52,60,.16);
        }

        .layers-panel {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: #e9edf0;
          color: #1b2a30;
          border-left: 1px solid #9eafb5;
          box-shadow: -8px 0 24px rgba(32,52,60,.16);
        }

        .layers-panel-head {
          min-height: 82px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 18px;
          background: #243c47;
          color: #f4f7f7;
          border-bottom: 3px solid #73939e;
        }

        .drawer-eyebrow {
          font-size: 9px;
          letter-spacing: .17em;
          font-weight: 800;
          color: #a9c0c7;
        }

        .drawer-title {
          margin-top: 5px;
          font-size: 16px;
          line-height: 1;
          font-weight: 800;
          letter-spacing: .06em;
        }

        .drawer-close {
          width: 30px;
          height: 30px;
          border: 1px solid #718d97;
          background: #1c3039;
          color: #f2f6f6;
          font-size: 19px;
          line-height: 1;
        }

        .drawer-close:hover { background: #315664; }

        .layers-panel-body {
          padding: 12px;
          display: grid;
          gap: 7px;
        }

        .layer-row {
          width: 100%;
          min-height: 58px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          padding: 0 13px;
          border: 1px solid #b8c5ca;
          background: #f8faf9;
          color: #40565e;
          text-align: left;
          transition: .16s ease;
        }

        .layer-row:hover {
          border-color: #6f8e98;
          background: #f4f7f7;
        }

        .layer-row.is-on {
          border-left: 4px solid #4c7b89;
          padding-left: 10px;
        }

        .layer-label {
          font-size: 10px;
          font-weight: 800;
          letter-spacing: .09em;
        }

        .layer-switch {
          width: 38px;
          height: 20px;
          padding: 2px;
          border: 1px solid #9db0b7;
          background: #d9e0e2;
          border-radius: 999px;
          flex: 0 0 auto;
        }

        .layer-switch span {
          display: block;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #7d8c91;
          transition: transform .16s ease, background .16s ease;
        }

        .layer-switch.is-on {
          background: #c7dbe0;
          border-color: #5f8997;
        }

        .layer-switch.is-on span {
          transform: translateX(17px);
          background: #356776;
        }

        .layers-panel-foot {
          margin-top: auto;
          padding: 13px 15px;
          border-top: 1px solid #c1cdd1;
          background: #e1e7e9;
          font-size: 8px;
          line-height: 1.5;
          letter-spacing: .1em;
          color: #65767d;
        }

        .layers-panel-foot b {
          display: block;
          margin-top: 3px;
          color: #40565e;
        }

        .timeline-glass-shell {
          position: absolute;
          left: 50%;
          bottom: 18px;
          z-index: 30;
          width: min(720px, calc(100% - 130px));
          transform: translateX(-50%);
          padding: 10px 14px;
          border: 1px solid rgba(224,238,241,.68);
          border-radius: 8px;
          background: rgba(30,51,60,.72);
          box-shadow: 0 8px 26px rgba(22,42,49,.20);
          backdrop-filter: blur(14px) saturate(120%);
        }

        .timeline-glass-shell {
          color: #182b32;
        }

        .timeline-glass-shell label,
        .timeline-glass-shell span,
        .timeline-glass-shell div,
        .timeline-glass-shell button {
          color: #182b32 !important;
          font-weight: 700;
        }

        .timeline-glass-shell input[type="range"] {
          color: #8fb5bf;
        }

        .timeline-glass-shell input[type="range"] {
          width: 100%;
          accent-color: #8fb5bf;
          cursor: pointer;
        }

        .timeline-glass-shell input[type="range"]::-webkit-slider-runnable-track {
          height: 5px;
          border-radius: 99px;
          background: rgba(226,239,242,.55);
        }

        .timeline-glass-shell input[type="range"]::-webkit-slider-thumb {
          width: 16px;
          height: 16px;
          margin-top: -5.5px;
          border: 2px solid #f2f7f7;
          border-radius: 50%;
          background: #4e7d8b;
          box-shadow: 0 2px 8px rgba(0,0,0,.28);
          -webkit-appearance: none;
        }

        .timeline-glass-shell input[type="range"]::-moz-range-track {
          height: 5px;
          border-radius: 99px;
          background: rgba(226,239,242,.55);
        }

        .timeline-glass-shell input[type="range"]::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border: 2px solid #f2f7f7;
          border-radius: 50%;
          background: #4e7d8b;
        }

        .timeline-glass-shell button {
          color: #f4f8f8 !important;
        }

        .timeline-glass-shell label,
        .timeline-glass-shell span,
        .timeline-glass-shell div {
          text-shadow: none;
        }

        .polar-console {
          background: #e9edf0;
          color: #18262c;
          border-left: 1px solid #aebbc1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }

        .polar-console-header {
          height: 62px;
          flex: 0 0 62px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 18px;
          background: #243c47;
          color: #f4f7f7;
          border-bottom: 3px solid #73939e;
        }

        .console-eyebrow {
          font-size: 10px;
          line-height: 1;
          letter-spacing: .17em;
          font-weight: 800;
          color: #a9c0c7;
        }

        .console-heading {
          margin-top: 5px;
          font-size: 17px;
          line-height: 1;
          letter-spacing: .04em;
          font-weight: 800;
        }

        .console-time {
          min-width: 56px;
          padding: 7px 9px;
          text-align: center;
          border: 1px solid #718d97;
          background: #1c3039;
          font: 800 11px/1 ui-monospace, monospace;
          letter-spacing: .08em;
          color: #f2f6f6;
        }

        .console-body {
          flex: 1;
          min-height: 0;
          padding: 10px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          grid-template-rows: auto auto auto auto;
          gap: 8px;
          overflow: hidden;
        }

        .console-card {
          width: 100%;
          min-width: 0;
          border: 1px solid #aebcc2;
          background: #f8faf9;
          color: #1b2a30;
          text-align: left;
          box-shadow: 0 1px 0 rgba(25,45,52,.05);
          border-radius: 3px;
        }

        .console-card:hover {
          border-color: #6f8e98;
          box-shadow: 0 2px 8px rgba(34,55,63,.10);
        }

        .card-head {
          min-height: 31px;
          padding: 8px 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid #d2dade;
          font-size: 10px;
          line-height: 1;
          font-weight: 800;
          letter-spacing: .12em;
          color: #52666e;
        }

        .data-state,
        .open-label {
          font: 800 9px/1 ui-monospace, monospace;
          letter-spacing: .07em;
          color: #547985;
        }

        .environment-card {
          grid-column: 1 / -1;
        }

        .metric-strip {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          min-height: 64px;
        }

        .metric {
          padding: 10px;
          border-right: 1px solid #d7dfe2;
        }

        .metric:last-child {
          border-right: 0;
        }

        .metric span,
        .route-metrics span,
        .iceberg-stats span,
        .route-risk span,
        .metric-label {
          display: block;
          font-size: 9px;
          font-weight: 750;
          letter-spacing: .09em;
          color: #708087;
        }

        .metric strong {
          display: block;
          margin-top: 7px;
          font: 800 15px/1 ui-monospace, monospace;
          color: #1d333c;
        }

        .iceberg-card {
          padding-bottom: 0;
          cursor: pointer;
        }

        .iceberg-main {
          min-height: 70px;
          padding: 11px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .iceberg-id {
          font: 900 22px/1 ui-monospace, monospace;
          letter-spacing: .03em;
          color: #183743;
        }

        .iceberg-position {
          margin-top: 7px;
          font: 11px/1.2 ui-monospace, monospace;
          color: #61747b;
        }

        .risk-badge {
          padding: 7px 8px;
          border: 1px solid #aebcc2;
          font: 900 9px/1 ui-monospace, monospace;
          letter-spacing: .08em;
          background: #edf1f1;
          color: #536970;
        }

        .risk-high {
          border-color: #a9695e;
          background: #f3e4e0;
          color: #7b382e;
        }

        .risk-medium {
          border-color: #aa9465;
          background: #f3ecdc;
          color: #765d2b;
        }

        .risk-low {
          border-color: #83a0a7;
          background: #e6eff1;
          color: #365e68;
        }

        .iceberg-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          border-top: 1px solid #d2dade;
          background: #eef2f3;
        }

        .iceberg-stats > div {
          padding: 8px 10px;
          border-right: 1px solid #d2dade;
        }

        .iceberg-stats > div:last-child {
          border-right: 0;
        }

        .iceberg-stats strong {
          display: block;
          margin-top: 4px;
          font: 800 11px/1 ui-monospace, monospace;
          color: #203a44;
        }

        .route-card {
          grid-column: 1 / -1;
          overflow: hidden;
        }

        .route-high {
          border-left: 4px solid #a9695e;
        }

        .route-medium {
          border-left: 4px solid #aa9465;
        }

        .route-profile-row {
          padding: 10px;
          display: flex;
          justify-content: space-between;
          align-items: end;
        }

        .route-profile {
          display: block;
          margin-top: 5px;
          font-size: 15px;
          letter-spacing: .04em;
          color: #1a3b47;
        }

        .route-risk {
          text-align: right;
        }

        .route-risk strong {
          display: block;
          margin-top: 5px;
          font: 900 13px/1 ui-monospace, monospace;
        }

        .route-metrics {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          border-top: 1px solid #d2dade;
          border-bottom: 1px solid #d2dade;
          background: #eef2f3;
        }

        .route-metrics > div {
          padding: 8px 10px;
          border-right: 1px solid #d2dade;
        }

        .route-metrics > div:last-child {
          border-right: 0;
        }

        .route-metrics strong {
          display: block;
          margin-top: 4px;
          font: 800 12px/1 ui-monospace, monospace;
          color: #213b45;
        }

        .reassess-command,
        .modal-command {
          width: 100%;
          min-height: 37px;
          border: 0;
          background: #2e5663;
          color: #f8fbfb;
          font-size: 10px;
          font-weight: 900;
          letter-spacing: .13em;
          cursor: pointer;
        }

        .reassess-command:hover,
        .modal-command:hover {
          background: #234550;
        }

        .reassess-command:disabled,
        .modal-command:disabled {
          cursor: wait;
          opacity: .55;
        }

        .empty-route {
          padding: 11px;
          font-size: 10px;
          color: #728188;
        }

        .empty-route .reassess-command {
          margin-top: 9px;
        }

        .hazard-card,
        .intelligence-card {
          cursor: pointer;
          overflow: hidden;
        }

        .hazard-preview {
          min-height: 66px;
        }

        .hazard-row {
          display: grid;
          grid-template-columns: 8px 1fr auto auto;
          align-items: center;
          gap: 7px;
          padding: 8px 10px;
          border-bottom: 1px solid #e0e5e7;
          font-size: 10px;
        }

        .hazard-row strong {
          font: 900 11px/1 ui-monospace, monospace;
        }

        .hazard-row span:not(.hazard-dot) {
          font: 800 9px/1 ui-monospace, monospace;
          color: #687a81;
        }

        .hazard-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
        }

        .dot-high { background: #9c5449; }
        .dot-medium { background: #a58445; }
        .dot-low { background: #668c96; }

        .alert-count {
          color: #8d4439;
          font: 900 9px/1 ui-monospace, monospace;
          letter-spacing: .06em;
        }

        .clear-hazard {
          padding: 16px 10px;
          font: 800 9px/1 ui-monospace, monospace;
          color: #718188;
        }

        .card-action {
          padding: 7px 10px;
          border-top: 1px solid #d2dade;
          background: #eef2f3;
          font: 900 9px/1 ui-monospace, monospace;
          letter-spacing: .08em;
          color: #547985;
        }

        .intel-preview {
          height: 66px;
          padding: 10px;
          overflow: hidden;
          font-size: 11px;
          line-height: 1.45;
          color: #435860;
        }

        .qwen-mark {
          font: 800 8px/1 ui-monospace, monospace;
          letter-spacing: .06em;
          color: #547985;
        }

        .route-compare {
          grid-column: 1 / -1;
        }

        .route-option-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 6px;
          padding: 8px;
        }

        .route-option {
          min-height: 48px;
          padding: 7px;
          border: 1px solid #c4d0d4;
          background: #f0f3f4;
          text-align: left;
        }

        .route-option:hover {
          background: #e4ebed;
        }

        .route-option span {
          display: block;
          font: 800 8px/1 ui-monospace, monospace;
          color: #667980;
        }

        .route-option strong {
          display: block;
          margin-top: 7px;
          font: 900 11px/1 ui-monospace, monospace;
          color: #24434e;
        }

        .route-selected {
          border-color: #628895;
          background: #dfeaed;
          box-shadow: inset 0 0 0 1px #628895;
        }

        /* MODAL / POPUP */
        .console-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 2000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: rgba(19, 34, 40, .46);
        }

        .console-modal {
          width: min(680px, 92vw);
          max-height: 82vh;
          overflow-y: auto;
          background: #f7f9f8;
          border: 1px solid #839aa2;
          border-top: 5px solid #2e5663;
          box-shadow: 0 18px 50px rgba(16, 34, 41, .25);
          color: #1d3037;
        }

        .modal-header {
          min-height: 68px;
          padding: 13px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid #ccd6da;
          background: #e9eef0;
        }

        .modal-title {
          margin-top: 5px;
          font-size: 19px;
          font-weight: 900;
          letter-spacing: .04em;
          color: #203a44;
        }

        .modal-close {
          padding: 7px 9px;
          border: 1px solid #aebdc2;
          background: #f5f7f7;
          font: 800 9px/1 ui-monospace, monospace;
          color: #52666e;
        }

        .modal-content {
          padding: 16px;
        }

        .modal-intro,
        .modal-note {
          font-size: 12px;
          line-height: 1.55;
          color: #53676f;
        }

        .modal-hazard-list {
          margin-top: 13px;
          border: 1px solid #ccd6da;
        }

        .modal-hazard {
          min-height: 62px;
          padding: 11px 13px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 1px solid #d7dfe2;
        }

        .modal-hazard:last-child {
          border-bottom: 0;
        }

        .modal-hazard strong {
          display: block;
          font: 900 14px/1 ui-monospace, monospace;
          color: #203a44;
        }

        .modal-hazard span {
          display: block;
          margin-top: 6px;
          font: 800 9px/1 ui-monospace, monospace;
          color: #718188;
        }

        .modal-empty {
          padding: 22px;
          text-align: center;
          font: 800 10px/1 ui-monospace, monospace;
          color: #718188;
        }

        .modal-command {
          margin-top: 14px;
          min-height: 42px;
        }

        .intel-block,
        .intel-recommendation,
        .decision-basis-modal {
          padding: 12px;
          margin-bottom: 9px;
          border: 1px solid #ccd6da;
          background: #eef2f3;
        }

        .intel-block span,
        .intel-recommendation span,
        .decision-basis-modal span {
          font: 900 9px/1 ui-monospace, monospace;
          letter-spacing: .1em;
          color: #61747b;
        }

        .intel-block p,
        .intel-recommendation p,
        .decision-basis-modal p {
          margin-top: 7px;
          font-size: 12px;
          line-height: 1.55;
          color: #334b54;
        }

        .intel-recommendation {
          border-left: 4px solid #547985;
          background: #e4edef;
        }

        .full-route {
          padding: 13px;
          margin-bottom: 8px;
          border: 1px solid #ccd6da;
          background: #eef2f3;
        }

        .full-route-selected {
          border-color: #628895;
          background: #e1ecee;
          box-shadow: inset 3px 0 #628895;
        }

        .full-route > div:first-child {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .full-route > div:first-child strong {
          font-size: 13px;
          letter-spacing: .04em;
        }

        .full-route > div:first-child span {
          font: 900 9px/1 ui-monospace, monospace;
          color: #547985;
        }

        .full-route-metrics {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          margin-top: 12px;
        }

        .full-route-metrics span {
          font: 800 9px/1.2 ui-monospace, monospace;
          color: #718188;
        }

        .full-route-metrics b {
          display: block;
          margin-top: 4px;
          font-size: 11px;
          color: #203a44;
        }

        .iceberg-modal-hero {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 15px;
          border: 1px solid #ccd6da;
          background: #e9eef0;
        }

        .big-iceberg-id {
          font: 900 28px/1 ui-monospace, monospace;
          color: #1f3c47;
        }

        .modal-risk {
          font-size: 10px;
        }

        .modal-data-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1px;
          margin-top: 10px;
          background: #ccd6da;
          border: 1px solid #ccd6da;
        }

        .modal-data-grid > div {
          padding: 12px;
          background: #f7f9f8;
        }


        .timeline-glass-shell .text-xs,
        .timeline-glass-shell .text-sm {
          color: #182b32 !important;
          font-weight: 800 !important;
        }

        .timeline-glass-shell .font-mono {
          color: #182b32 !important;
        }

        @media (max-width: 1200px) {
          .console-body {
            grid-template-columns: 1fr;
            overflow-y: auto;
          }

          .environment-card,
          .route-card,
          .route-compare {
            grid-column: auto;
          }
        }
      `}</style>

      {missionNotification && (
        <div className="fixed right-5 top-5 z-[1000] w-[360px] border border-[#cdd2cf] bg-[#fafaf8] shadow-lg">
          <div
            className={`h-1 ${
              missionNotification.type === "HIGH"
                ? "bg-[#a84d43]"
                : missionNotification.type === "MEDIUM"
                  ? "bg-[#876d3f]"
                  : "bg-[#365e72]"
            }`}
          />

          <div className="px-4 py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle
                size={17}
                className={
                  missionNotification.type === "HIGH"
                    ? "text-[#a84d43]"
                    : missionNotification.type === "MEDIUM"
                      ? "text-[#876d3f]"
                      : "text-[#365e72]"
                }
              />

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[9px] font-semibold tracking-[0.16em] text-[#59666a]">
                    MISSION INTELLIGENCE
                  </span>

                  <button
                    onClick={() => setMissionNotification(null)}
                    className="text-[16px] leading-none text-[#8a9496] hover:text-[#263337]"
                    aria-label="Dismiss notification"
                  >
                    ×
                  </button>
                </div>

                <div className="mt-2 font-mono text-[11px] font-semibold tracking-wide text-[#263337]">
                  {missionNotification.title}
                </div>

                <p className="mt-2 text-[10px] leading-relaxed text-[#687579]">
                  {missionNotification.message}
                </p>

                {missionNotification.type !== "INFO" && (
                  <button
                    onClick={() => {
                      setMissionNotification(null);

                      document
                        .getElementById("route-hazard-watch")
                        ?.scrollIntoView({
                          behavior: "smooth",
                          block: "center",
                        });
                    }}
                    className="mt-3 border border-[#b8c0bf] px-3 py-1.5 font-mono text-[9px] tracking-wider text-[#59666a] hover:bg-[#eef1ef]"
                  >
                    VIEW HAZARD
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

/* ==================================================
   DATA FIELD
   ================================================== */

function Data({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] text-[#7a8588]">{label}</div>

      <div className="mt-1 font-mono text-[11px]">{value}</div>
    </div>
  );
}

/* ==================================================
   GLOBAL ROUTE HAZARD WATCH
   ================================================== */

function GlobalRouteHazardWatch({
  hazards,
  selectedIcebergId,
  onReassessRoute,
  loading,
}: {
  hazards: {
    iceberg_id: string;
    minimum_separation_km: number;
    uncertainty_radius_km: number;
    effective_separation_km: number;
    risk_level: string;
    is_route_hazard: boolean;
  }[];
  selectedIcebergId: string;
  onReassessRoute: () => void;

  loading: boolean;
}) {
  const routeHazards = hazards.filter((hazard) => hazard.is_route_hazard);

  const unselectedHazards = routeHazards.filter(
    (hazard) => hazard.iceberg_id !== selectedIcebergId,
  );

  const visibleHazards = hazards
    .filter(
      (hazard) =>
        hazard.is_route_hazard || hazard.iceberg_id === selectedIcebergId,
    )
    .slice(0, 5);

  return (
    <div id="route-hazard-watch" className="border-b border-[#cdd2cf]">
      <div className="px-5 py-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
            ROUTE HAZARD WATCH
          </span>

          {unselectedHazards.length > 0 && (
            <span className="text-[9px] font-semibold tracking-wider text-[#8a4b3d]">
              ATTENTION
            </span>
          )}
        </div>

        <div className="mt-1 text-[9px] leading-relaxed text-[#7a8587]">
          Independent scan of all detected icebergs against the recommended
          passage corridor.
        </div>
      </div>

      {unselectedHazards.length > 0 && (
        <div className="mx-5 mb-3 border border-[#d8c5bf] bg-[#f5eeee] px-3 py-3">
          <div className="flex items-start gap-2">
            <AlertTriangle
              size={14}
              strokeWidth={1.8}
              className="mt-[1px] shrink-0 text-[#8a4b3d]"
            />

            <div>
              <div className="text-[10px] font-semibold tracking-[0.08em] text-[#6f3d32]">
                {unselectedHazards.length} UNSELECTED ROUTE HAZARD
                {unselectedHazards.length > 1 ? "S" : ""}
              </div>

              <div className="mt-1 text-[9px] leading-relaxed text-[#6d7475]">
                A detected iceberg other than the selected target lies within
                the operational hazard corridor.
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="divide-y divide-[#e0e3e1]">
        {visibleHazards.length === 0 ? (
          <div className="px-5 py-4 text-[9px] text-[#7a8587]">
            NO ICEBERG WITHIN OPERATIONAL CORRIDOR
          </div>
        ) : (
          visibleHazards.map((hazard) => {
            const selected = hazard.iceberg_id === selectedIcebergId;

            return (
              <div key={hazard.iceberg_id} className="px-5 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        hazard.risk_level === "HIGH"
                          ? "bg-[#8a4b3d]"
                          : hazard.risk_level === "MEDIUM"
                            ? "bg-[#9a7440]"
                            : "bg-[#6f858c]"
                      }`}
                    />

                    <span className="font-mono text-[10px] font-semibold text-[#263337]">
                      {hazard.iceberg_id.toUpperCase()}
                    </span>

                    {selected && (
                      <span className="text-[8px] font-semibold tracking-[0.12em] text-[#365e72]">
                        SELECTED
                      </span>
                    )}

                    {!selected && hazard.is_route_hazard && (
                      <span className="text-[8px] font-semibold tracking-[0.12em] text-[#8a4b3d]">
                        UNSELECTED HAZARD
                      </span>
                    )}
                  </div>

                  <span className="font-mono text-[10px] text-[#263337]">
                    {hazard.effective_separation_km.toFixed(1)} km
                  </span>
                </div>

                <div className="mt-1 pl-3.5 text-[8px] tracking-[0.08em] text-[#7a8587]">
                  {hazard.risk_level} · EFFECTIVE SEPARATION
                </div>
              </div>
            );
          })
        )}
      </div>

      {unselectedHazards.length > 0 && (
        <div className="border-t border-[#d8c5bf] px-5 py-3">
          <button
            type="button"
            onClick={onReassessRoute}
            disabled={loading}
            className={`w-full border border-[#8a4b3d] px-3 py-2 text-[9px] font-semibold tracking-[0.12em] text-[#6f3d32] transition-colors ${
              loading ? "cursor-wait opacity-60" : "hover:bg-[#f5eeee]"
            }`}
          >
            {loading
              ? selectedHour > 0
                ? `REASSESSING +${selectedHour}H...`
                : "CALCULATING..."
              : selectedHour > 0
                ? `REASSESS +${selectedHour}H ROUTE`
                : "CALCULATE ROUTE"}
          </button>
        </div>
      )}
    </div>
  );
}
