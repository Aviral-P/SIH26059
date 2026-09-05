"use client";

import { useEffect, useState } from "react";

export interface IcebergObservation {
  iceberg_id: string;
  observed_at: string;
  latitude: number;
  longitude: number;
  displacement_km: number | null;
  velocity_kmh: number | null;
  velocity_angle_deg: number | null;
}

interface IcebergResponse {
  date: string;
  count: number;
  icebergs: IcebergObservation[];
}

export function useIcebergs(date = "20230721") {
  const [icebergs, setIcebergs] = useState<IcebergObservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchIcebergs() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `http://localhost:8000/api/v1/icebergs?date=${date}&min_lat=-75&max_lat=-55&min_lon=-180&max_lon=180`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: IcebergResponse = await response.json();

        setIcebergs(data.icebergs);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load iceberg observations"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchIcebergs();
  }, [date]);

  return {
    icebergs,
    loading,
    error,
  };
}