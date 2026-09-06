export interface ForecastResponse {
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

  trajectory: Array<{
    hours: number;
    latitude: number;
    longitude: number;
    environment?: {
      timestamp?: string;
      latitude?: number;
      longitude?: number;
      sea_ice_percent?: number | null;
      wind_mps?: number | null;
      current_mps?: number | null;
      sea_ice_available?: boolean;
      wind_available?: boolean;
      current_available?: boolean;
    } | null;
  }>;
}