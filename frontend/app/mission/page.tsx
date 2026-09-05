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

export default function Home() {
  /*
   * ==================================================
   * STATE
   * ==================================================
   */

  const [selectedHour, setSelectedHour] = useState(0);

  /*
   * Selected iceberg defaults to D29C for the
   * validation scenario, but is fully dynamic.
   */

  const [selectedIcebergId, setSelectedIcebergId] = useState("d29c");

  /*
   * ==================================================
   * MISSION PARAMETERS
   * ==================================================
   *
   * These are now real application state instead of
   * hardcoded values inside the JSX/API request.
   *
   * Defaults preserve the current validation scenario.
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
   *
   * Prevent duplicate forecast requests from running
   * simultaneously.
   *
   * We also track WHICH iceberg the request belongs to,
   * so a request for D29C cannot block a new request for
   * another selected iceberg.
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

  /*
   * Keep track of which iceberg the current forecast
   * actually belongs to.
   *
   * This prevents an old D29C forecast from appearing
   * after the user selects another iceberg.
   */

  const [forecastIcebergId, setForecastIcebergId] = useState<string | null>(
    null,
  );

  /*
   * ==================================================
   * MISSION PLAN
   * ==================================================
   */

  const { missionPlan, missionLoading, missionError, calculateRoutes } =
    useMissionPlan();

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
   *
   * Whenever the selected iceberg changes:
   *
   * 1. Find its real observation.
   * 2. Send that observation to the forecast API.
   * 3. Store the returned forecast.
   *
   * No hardcoded iceberg coordinates are used here.
   */

  useEffect(() => {
    /*
     * Wait until the iceberg API has finished loading.
     */

    if (icebergsLoading) {
      return;
    }

    /*
     * If the selected iceberg doesn't exist,
     * clear any old forecast.
     */

    if (!selectedIceberg) {
      setForecast(null);
      setForecastIcebergId(null);
      setForecastError(null);
      setForecastLoading(false);
      return;
    }

    const iceberg = selectedIceberg;

    /*
     * Each effect instance gets its own cancellation flag.
     *
     * This prevents an old request from updating state
     * after the user selects another iceberg.
     */

    let cancelled = false;

    /*
     * Prevent duplicate requests for the SAME iceberg.
     *
     * A request for another iceberg is allowed to start
     * after the current request has completed.
     */

    if (
      forecastRequestInFlight.current &&
      forecastRequestIcebergId.current === iceberg.iceberg_id
    ) {
      return;
    }

    /*
     * Clear previous forecast immediately.
     *
     * This prevents D29C's forecast from being shown
     * while another iceberg is being processed.
     */

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

        /*
         * Ignore the response if the user has already
         * selected another iceberg.
         */

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
        /*
         * Release the request lock.
         */

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
   *
   * Only use a trajectory if it belongs to the
   * currently selected iceberg.
   */

  const selectedTrajectoryPoint =
    selectedHour > 0 && hasSelectedIcebergForecast && forecast?.trajectory
      ? forecast.trajectory.find((point) => point.hours === selectedHour)
      : undefined;

  /*
   * ==================================================
   * SELECTED ICEBERG POSITION
   * ==================================================
   *
   * At 0h:
   *   real observed position
   *
   * At +6/+12/+18/+24:
   *   forecast position, but only when a valid
   *   forecast exists for the selected iceberg.
   *
   * This is the TRACKED ICEBERG position,
   * not the vessel position.
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
   *
   * Current observed values are from the validated
   * Jul 21 2023 environmental dataset.
   *
   * We do not invent future values.
   */

  const environmentState = {
    seaIce: selectedHour <= 0 ? "85.6 %" : "FORECAST",

    wind: selectedHour <= 0 ? "15.20 m/s" : "FORECAST",

    current: selectedHour <= 0 ? "0.28 m/s" : "FORECAST",
  };

  const environmentType = selectedHour > 0 ? "FORECAST" : "OBSERVED";

  /*
   * ==================================================
   * ICEBERG SELECTION
   * ==================================================
   */

  const handleIcebergSelect = (icebergId: string) => {
    setSelectedIcebergId(icebergId);

    /*
     * Always return to the observed state when a
     * different iceberg is selected.
     */

    setSelectedHour(0);
  };

  /*
   * ==================================================
   * ROUTE CALCULATION
   * ==================================================
   *
   * Use:
   *   - real mission origin
   *   - real mission destination
   *   - selected vessel speed
   *   - selected iceberg position
   *
   * If a future forecast point exists, use that
   * iceberg position. Otherwise use its observation.
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

    await calculateRoutes({
      /*
       * REAL MISSION ORIGIN
       */
      start: {
        latitude: origin.latitude,

        longitude: origin.longitude,
      },

      /*
       * REAL MISSION DESTINATION
       */
      destination: {
        latitude: destination.latitude,

        longitude: destination.longitude,
      },

      /*
       * REAL MISSION VESSEL SPEED
       */
      vessel_speed_knots: vesselSpeed,

      iceberg_date: "20230721",

      /*
       * Selected iceberg is supplied to the route
       * risk calculation.
       */
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
  };

  /*
   * ==================================================
   * ROUTE HAZARD INTELLIGENCE
   * ==================================================
   */

  const recommendedEvaluation =
    missionPlan?.routes[missionPlan.recommended_profile]?.evaluation;

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

      <div className="grid grid-cols-[260px_1fr_300px] h-[calc(100vh-56px)]">
        {/* ==================================================
            LEFT CONTROL PANEL
            ================================================== */}

        <MissionControls
          /*
           * REAL MISSION PARAMETERS
           */
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
        />

        {/* ==================================================
            MAP
            ================================================== */}

        <section className="relative overflow-hidden bg-[#dce4e3]">
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

          {/* ==================================================
              LEAFLET MAP
              ================================================== */}

          <MissionMap
            /*
             * Current tracked iceberg position.
             *
             * This intentionally remains separate from
             * the vessel origin.
             */
            currentPosition={selectedIcebergPosition}
            /*
             * REAL VESSEL ORIGIN
             */
            vesselPosition={origin}
            /*
             * REAL DESTINATION
             */
            destination={destination}
            /*
             * Start trajectory from the real observed
             * position of the selected iceberg.
             */

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
            /*
             * Only show +24h forecast when the forecast
             * actually belongs to the selected iceberg.
             */

            forecastPosition={
              selectedHour === 24 && hasSelectedIcebergForecast && forecast
                ? {
                    latitude: forecast.forecast.latitude,

                    longitude: forecast.forecast.longitude,
                  }
                : undefined
            }
            /*
             * Only show uncertainty when the selected
             * iceberg has a valid forecast.
             */

            uncertaintyKm={
              selectedHour === 24 && hasSelectedIcebergForecast && forecast
                ? forecast.ensemble.uncertainty_radius_km
                : undefined
            }
            /*
             * Route alternatives generated by the
             * mission planner.
             */

            routes={missionPlan?.routes}
            recommendedProfile={missionPlan?.recommended_profile}
            riskLevel={recommendedEvaluation?.risk_level}
            riskCpaKm={recommendedEvaluation?.min_iceberg_separation_km ?? undefined}
            /*
             * Do not draw a stale trajectory belonging
             * to another iceberg.
             */

            trajectory={
              hasSelectedIcebergForecast ? forecast?.trajectory : undefined
            }
            /*
             * Real environmental/iceberg data.
             */

            seaIce={seaIceCells}
            icebergs={icebergs}
            selectedIcebergId={selectedIcebergId}
            onIcebergSelect={handleIcebergSelect}
          />

          {/* ==================================================
              TIMELINE
              ================================================== */}

          <MissionTimeline
            selectedHour={selectedHour}
            onSelectHour={setSelectedHour}
          />

          {/* ==================================================
              MAP LEGEND
              ================================================== */}

          <MissionLegend className="absolute bottom-5 left-6" />
        </section>

        {/* ==================================================
            RIGHT INTELLIGENCE PANEL
            ================================================== */}

        <aside className="border-l border-[#cdd2cf] bg-[#fafaf8] overflow-y-auto">
          {/* ==================================================
              ENVIRONMENT
              ================================================== */}

          <EnvironmentPanel
            seaIce={environmentState.seaIce}
            wind={environmentState.wind}
            current={environmentState.current}
            environmentType={environmentType}
            selectedHour={selectedHour}
          />

          {/* ==================================================
              SELECTED REAL ICEBERG
              ================================================== */}

          <div className="border-b border-[#cdd2cf] bg-[#f4f6f5] px-5 py-4">
            <div className="flex items-center justify-between">
              <span className="text-[9px] tracking-[0.15em] text-[#687579]">
                SELECTED ICEBERG
              </span>

              <span className="font-mono text-[9px] text-[#365e72]">
                {icebergsLoading
                  ? "LOADING"
                  : forecastLoading
                    ? "FORECAST"
                    : selectedIceberg
                      ? "OBSERVED"
                      : "—"}
              </span>
            </div>

            {selectedIceberg ? (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <Data label="ID" value={selectedIceberg.iceberg_id} />

                <Data
                  label="OBSERVED"
                  value={new Date(selectedIceberg.observed_at).toISOString()}
                />

                <Data
                  label="LATITUDE"
                  value={`${selectedIceberg.latitude.toFixed(3)}°`}
                />

                <Data
                  label="LONGITUDE"
                  value={`${selectedIceberg.longitude.toFixed(3)}°`}
                />
              </div>
            ) : (
              <div className="mt-3 text-[10px] text-[#7a8588]">
                No iceberg observation selected.
              </div>
            )}

            {icebergsError && (
              <div className="mt-3 text-[9px] text-[#a84d43]">
                {icebergsError}
              </div>
            )}

            {forecastError && (
              <div className="mt-3 text-[9px] text-[#a84d43]">
                Forecast unavailable for {selectedIcebergId}: {forecastError}
              </div>
            )}
          </div>

          {/* ==================================================
              ICEBERG FORECAST PANEL
              ================================================== */}

          <IcebergPanel
            selectedHour={selectedHour}
            icebergState={icebergState}
            /*
             * Only pass the forecast when it belongs
             * to the currently selected iceberg.
             */

            forecast={hasSelectedIcebergForecast ? forecast : null}
            cpaKm={
              missionPlan
                ? missionPlan.routes[missionPlan.recommended_profile]
                    ?.evaluation.min_iceberg_separation_km
                : undefined
            }
            selectedIcebergId={selectedIcebergId}
          />

          {/* ==================================================
              TEMPORAL STATE
              ================================================== */}

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
                value={selectedHour === 0 ? "NOW" : `+${selectedHour}h`}
              />

              <Data
                label="DATA TYPE"
                value={
                  selectedHour === 0
                    ? "OBSERVED"
                    : hasSelectedIcebergForecast
                      ? "FORECAST"
                      : "OBSERVED ONLY"
                }
              />
            </div>
          </div>

          {/* ==================================================
              ROUTE HAZARD
              ================================================== */}

          <div
            className={`border-b border-[#cdd2cf] px-5 py-4 ${
              hazardIsHigh
                ? "bg-[#f7eeee]"
                : hazardIsMedium
                  ? "bg-[#f5f1e9]"
                  : "bg-[#f4f6f5]"
            }`}
          >
            <div
              className={`flex items-center gap-2 ${
                hazardIsHigh
                  ? "text-[#a84d43]"
                  : hazardIsMedium
                    ? "text-[#876d3f]"
                    : "text-[#365e72]"
              }`}
            >
              {hazardIsHigh ? (
                <AlertTriangle size={15} />
              ) : (
                <div className="h-[7px] w-[7px] rounded-full border border-current" />
              )}

              <span className="text-[11px] font-semibold tracking-wider">
                {hazardTitle}
              </span>

              {recommendedRisk && (
                <span className="ml-auto font-mono text-[9px]">
                  {recommendedRisk}
                </span>
              )}
            </div>

            <p
              className={`mt-2 text-[11px] leading-relaxed ${
                hazardIsHigh
                  ? "text-[#5d4a47]"
                  : hazardIsMedium
                    ? "text-[#655b4a]"
                    : "text-[#59666a]"
              }`}
            >
              {hazardMessage}
            </p>

            {hasRouteEvaluation && (
              <div className="mt-3 border-t border-[#d5dad8] pt-3">
                <Data label="MINIMUM SEPARATION" value={hazardCpa} />
              </div>
            )}
          </div>

          {/* ==================================================
              MISSION INTELLIGENCE
              ================================================== */}

          {hasRouteEvaluation && recommendedEvaluation && (
            <div className="border-b border-[#cdd2cf] bg-[#fafaf8] px-5 py-4">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-semibold tracking-[0.16em] text-[#59666a]">
                  MISSION INTELLIGENCE
                </span>

                <span className="font-mono text-[9px] text-[#365e72]">
                  DECISION SUPPORT
                </span>
              </div>

              <div className="mt-3">
                <div className="text-[9px] tracking-[0.12em] text-[#7a8588]">
                  RECOMMENDED PROFILE
                </div>

                <div className="mt-1 font-mono text-[14px] font-semibold tracking-wide">
                  {missionPlan?.recommended_profile
                    ?.replaceAll("_", " ")
                    .toUpperCase()}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
                <Data label="MIN SEPARATION" value={hazardCpa} />

                <Data
                  label="OVERALL SCORE"
                  value={recommendedEvaluation.overall_score.toFixed(2)}
                />

                <Data
                  label="ICEBERG EXPOSURE"
                  value={recommendedEvaluation.iceberg_exposure.toFixed(2)}
                />

                <Data
                  label="SEA-ICE EXPOSURE"
                  value={recommendedEvaluation.sea_ice_exposure.toFixed(2)}
                />
              </div>

              <div className="mt-4 border-t border-[#d5dad8] pt-3">
                <div className="text-[9px] tracking-[0.12em] text-[#7a8588]">
                  DECISION BASIS
                </div>

                <p className="mt-2 text-[10px] leading-relaxed text-[#59666a]">
                  {getRouteDecisionBasis()?.text}
                </p>
              </div>
            </div>
          )}

          {/* ==================================================
              ROUTE ANALYSIS
              ================================================== */}

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
                        ? `${Math.floor(
                            evaluation.estimated_hours,
                          )}h ${Math.round(
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
                          ? `${evaluation.min_iceberg_separation_km.toFixed(
                              2,
                            )} km`
                          : "—",

                      icebergExposure:
                        evaluation?.iceberg_exposure != null
                          ? evaluation.iceberg_exposure.toFixed(2)
                          : "—",

                      seaIceExposure:
                        evaluation?.sea_ice_exposure != null
                          ? evaluation.sea_ice_exposure.toFixed(2)
                          : "—",

                      overallScore:
                        evaluation?.overall_score != null
                          ? evaluation.overall_score.toFixed(2)
                          : "—",

                      selected: missionPlan.recommended_profile === profile,
                    };
                  })
                : routes.map((route) => ({
                    ...route,
                    icebergExposure: "—",
                    seaIceExposure: "—",
                    overallScore: "—",
                  }))
            }
          />
        </aside>
      </div>

      {/* ==================================================
          FORECAST LOADING
          ================================================== */}

      {forecastLoading && (
        <div className="pointer-events-none fixed bottom-3 right-3 z-50 bg-[#172126] px-3 py-2 font-mono text-[9px] tracking-wider text-white">
          FORECASTING {selectedIcebergId.toUpperCase()}
          ...
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
