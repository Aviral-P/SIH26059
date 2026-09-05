"use client";

import { useEffect, useState } from "react";

export interface SeaIceCell {
  latitude: number;
  longitude: number;
  concentration: number;
}

interface SeaIceResponse {
  date: string;
  cells: SeaIceCell[];
}

export function useSeaIce(date = "20230721") {
  const [cells, setCells] = useState<SeaIceCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSeaIce() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `http://localhost:8000/api/v1/sea-ice?date=${date}&min_lat=-67&max_lat=-60&min_lon=-50&max_lon=-44`
        );

        if (!response.ok) {
          throw new Error(`Sea-ice request failed (${response.status})`);
        }

        const data: SeaIceResponse = await response.json();

        setCells(data.cells);
      } catch (error) {
        console.error("SEA ICE ERROR:", error);

        setError(
          error instanceof Error
            ? error.message
            : "Sea-ice request failed"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchSeaIce();
  }, [date]);

  return {
    cells,
    loading,
    error,
  };
}