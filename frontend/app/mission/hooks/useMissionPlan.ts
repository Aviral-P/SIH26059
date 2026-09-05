"use client";

import { useState } from "react";

interface MissionPoint {
  latitude: number;
  longitude: number;
}

interface MissionIceberg {
  iceberg_id: string;
  latitude: number;
  longitude: number;
}

interface MissionPlanRequest {
  start: {
    latitude: number;
    longitude: number;
  };
  destination: {
    latitude: number;
    longitude: number;
  };
  vessel_speed_knots: number;
  iceberg_date: string;
  icebergs: Array<{
    iceberg_id: string;
    latitude: number;
    longitude: number;
  }>;
}

export interface MissionRouteEvaluation {
  distance_km: number;
  estimated_hours: number;
  vessel_speed_knots: number;
  iceberg_exposure: number;
  sea_ice_exposure: number;
  min_iceberg_separation_km: number | null;
  risk_level: string;
  overall_score: number;
}

export interface MissionRoute {
  geometry: MissionPoint[];
  evaluation: MissionRouteEvaluation;
}

export interface MissionPlanResponse {
  status: string;
  recommended_profile: string;
  routes: Record<string, MissionRoute>;
}

interface BackendRoute {
  route?: {
    status: string;
    profile: string;
    distance_km: number;
    risk_score: number;
    points: MissionPoint[];
    iterations: number;
  };
  evaluation?: MissionRouteEvaluation;
}

interface BackendMissionPlanResponse {
  status: string;
  recommended_profile: string;
  routes: Record<string, BackendRoute>;
}

export function useMissionPlan() {
  const [missionPlan, setMissionPlan] =
    useState<MissionPlanResponse | null>(null);

  const [missionLoading, setMissionLoading] =
    useState(false);

  const [missionError, setMissionError] =
    useState<string | null>(null);

  async function calculateRoutes(
    request: MissionPlanRequest
  ) {
    try {
      setMissionLoading(true);
      setMissionError(null);

      const response = await fetch(
        "http://localhost:8000/api/v1/mission/plan",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Route planning failed (${response.status})`
        );
      }

      const data: BackendMissionPlanResponse =
        await response.json();

      /*
       * Normalize backend route names/shapes
       * into the frontend MissionPlan format.
       */
      const normalizedRoutes: Record<string, MissionRoute> = {};

      Object.entries(data.routes).forEach(
        ([profile, backendRoute]) => {
          if (
            !backendRoute.route ||
            !backendRoute.evaluation
          ) {
            return;
          }

          const frontendProfile =
            profile === "fuel_optimized"
              ? "fuel"
              : profile;

          normalizedRoutes[frontendProfile] = {
            geometry: backendRoute.route.points,
            evaluation: backendRoute.evaluation,
          };
        }
      );

      const normalizedRecommendedProfile =
        data.recommended_profile === "fuel_optimized"
          ? "fuel"
          : data.recommended_profile;

      const normalizedData: MissionPlanResponse = {
        status: data.status,
        recommended_profile:
          normalizedRecommendedProfile,
        routes: normalizedRoutes,
      };

      setMissionPlan(normalizedData);

      return normalizedData;
    } catch (error) {
      console.error("MISSION PLAN ERROR:", error);

      const message =
        error instanceof Error
          ? error.message
          : "Route planning request failed";

      setMissionError(message);

      return null;
    } finally {
      setMissionLoading(false);
    }
  }

  return {
    missionPlan,
    missionLoading,
    missionError,
    calculateRoutes,
  };
}