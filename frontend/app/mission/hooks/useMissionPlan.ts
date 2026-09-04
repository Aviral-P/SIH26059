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
  start: MissionPoint;
  destination: MissionPoint;
  vessel_speed_knots: number;
  icebergs: MissionIceberg[];
  sea_ice: unknown[];
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
  geometry: Array<{
    latitude: number;
    longitude: number;
  }>;
  evaluation: MissionRouteEvaluation;
}

export interface MissionPlanResponse {
  status: string;
  recommended_profile: string;
  routes: Record<string, MissionRoute>;
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

      const data: MissionPlanResponse =
        await response.json();

      setMissionPlan(data);

      return data;
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