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
}