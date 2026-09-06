import { useState } from "react";

export interface IcebergRouteHazard {
  iceberg_id: string;
  minimum_separation_km: number;
  uncertainty_radius_km: number;
  effective_separation_km: number;
  risk_level: string;
  is_route_hazard: boolean;
}

export interface MissionRouteEvaluation {
  distance_km: number;
  estimated_hours: number;
  vessel_speed_knots: number;
  iceberg_exposure: number;
  sea_ice_exposure: number;

  max_sea_ice_concentration?: number;

  // Keep the ORIGINAL name used by page.tsx
  min_iceberg_separation_km: number | null;

  risk_level: string;
  overall_score: number;

  // NEW
  iceberg_hazards: IcebergRouteHazard[];
}

export interface MissionRoute {
  points: {
    latitude: number;
    longitude: number;
  }[];
}

export interface BackendMissionRoute {
  route: MissionRoute;
  evaluation: MissionRouteEvaluation;
}

export interface MissionPlanResponse {
  status: string;
  recommended_profile: string;

  routes: {
    safest?: BackendMissionRoute;
    balanced?: BackendMissionRoute;
    fuel_optimized?: BackendMissionRoute;
  };
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

  icebergs: {
    iceberg_id?: string;
    id?: string;
    source_id?: string;

    // Keep ORIGINAL names used by page.tsx
    latitude: number;
    longitude: number;

    uncertainty_radius_km?: number;

    [key: string]: unknown;
  }[];
}

export interface NormalizedMissionRoute {
  profile: string;

  points: {
    latitude: number;
    longitude: number;
  }[];

  evaluation: MissionRouteEvaluation;
}

export interface NormalizedMissionPlan {
  status: string;
  recommended_profile: string;
  routes: Record<string, NormalizedMissionRoute>;
}

export function useMissionPlan() {
  const [missionPlan, setMissionPlan] =
    useState<NormalizedMissionPlan | null>(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  async function calculateRoutes(
    request: MissionPlanRequest,
  ) {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        "http://localhost:8000/api/v1/mission/plan",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify(request),
        },
      );

      if (!response.ok) {
        throw new Error(
          `Mission planning failed: ${response.status}`,
        );
      }

      const data: MissionPlanResponse =
        await response.json();

      if (data.status !== "success") {
        throw new Error(
          "Mission planner returned an unsuccessful response.",
        );
      }

      const normalizedRoutes: Record<
        string,
        NormalizedMissionRoute
      > = {};

      Object.entries(data.routes).forEach(
        ([profile, result]) => {
          if (
            !result ||
            !result.route ||
            !result.evaluation
          ) {
            return;
          }

          normalizedRoutes[profile] = {
            profile,

            points: result.route.points,

            evaluation: {
              ...result.evaluation,

              // Safe fallback for older backend responses
              iceberg_hazards:
                result.evaluation.iceberg_hazards ?? [],
            },
          };
        },
      );

      const normalizedPlan: NormalizedMissionPlan = {
        status: data.status,

        recommended_profile:
          data.recommended_profile,

        routes: normalizedRoutes,
      };

      setMissionPlan(normalizedPlan);

      return normalizedPlan;
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to calculate mission routes.";

      setError(message);

      return null;
    } finally {
      setLoading(false);
    }
  }

  function clearMissionPlan() {
    setMissionPlan(null);
    setError(null);
  }

  return {
    missionPlan,

    // IMPORTANT:
    // Keep the names your existing page.tsx expects.
    missionLoading: loading,
    missionError: error,

    calculateRoutes,
    clearMissionPlan,
  };
}