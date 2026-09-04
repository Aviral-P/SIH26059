"use client";

import { useEffect, useRef } from "react";

interface Position {
  latitude: number;
  longitude: number;
}

interface RouteGeometryPoint {
  latitude: number;
  longitude: number;
}

interface MissionRoute {
  geometry: RouteGeometryPoint[];
}

interface MissionRoutes {
  safest?: MissionRoute;
  balanced?: MissionRoute;
  fuel?: MissionRoute;
}

interface MissionMapProps {
  currentPosition: Position;
  vesselPosition: Position;
  destinationPosition: Position;
  forecastPosition?: Position;
  uncertaintyKm?: number;
  routes?: MissionRoutes;
  recommendedProfile?: string;
}

export default function MissionMap({
  currentPosition,
  vesselPosition,
  destinationPosition,
  forecastPosition,
  uncertaintyKm,
  routes,
  recommendedProfile,
}: MissionMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function initializeMap() {
      if (!containerRef.current || mapRef.current) return;

      const L = await import("leaflet");

      if (cancelled || !containerRef.current || mapRef.current) {
        return;
      }

      const map = L.map(containerRef.current, {
        center: [
          currentPosition.latitude,
          currentPosition.longitude,
        ],
        zoom: 4,
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        dragging: true,
        touchZoom: true,
        boxZoom: true,
        keyboard: true,
      });

      mapRef.current = map;

      /*
       * OpenStreetMap base layer
       */
      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        }
      ).addTo(map);

      /*
       * Route drawing
       */
      const drawRoute = (
        route: MissionRoute | undefined,
        options: import("leaflet").PolylineOptions
      ) => {
        if (!route?.geometry?.length) return;

        const points = route.geometry.map(
          (point) =>
            [point.latitude, point.longitude] as [number, number]
        );

        L.polyline(points, options).addTo(map);
      };

      const routeStyles = {
        safest: {
          weight: 2,
          opacity: 0.45,
          dashArray: "6 6",
        },
        balanced: {
          weight: 2,
          opacity: 0.45,
          dashArray: "6 6",
        },
        fuel: {
          weight: 2,
          opacity: 0.45,
          dashArray: "2 6",
        },
      };

      const recommendedStyle = {
        weight: 4,
        opacity: 0.95,
      };

      drawRoute(
        routes?.safest,
        recommendedProfile === "safest"
          ? recommendedStyle
          : routeStyles.safest
      );

      drawRoute(
        routes?.balanced,
        recommendedProfile === "balanced"
          ? recommendedStyle
          : routeStyles.balanced
      );

      drawRoute(
        routes?.fuel,
        recommendedProfile === "fuel"
          ? recommendedStyle
          : routeStyles.fuel
      );

      /*
       * Vessel marker
       */
      const vesselMarker = L.circleMarker(
        [
          vesselPosition.latitude,
          vesselPosition.longitude,
        ],
        {
          radius: 7,
          weight: 2,
        }
      ).addTo(map);

      vesselMarker.bindTooltip("VESSEL", {
        permanent: true,
        direction: "bottom",
        offset: [0, 8],
      });

      /*
       * Destination marker
       */
      const destinationMarker = L.circleMarker(
        [
          destinationPosition.latitude,
          destinationPosition.longitude,
        ],
        {
          radius: 7,
          weight: 2,
          fillOpacity: 0.15,
        }
      ).addTo(map);

      destinationMarker.bindTooltip("DESTINATION", {
        permanent: true,
        direction: "top",
        offset: [0, -8],
      });

      /*
       * Forecast position
       */
      if (forecastPosition) {
        L.circleMarker(
          [
            forecastPosition.latitude,
            forecastPosition.longitude,
          ],
          {
            radius: 5,
            weight: 2,
          }
        )
          .bindTooltip("+24H FORECAST", {
            permanent: true,
            direction: "bottom",
            offset: [0, 8],
          })
          .addTo(map);
      }

      /*
       * Uncertainty radius
       */
      if (forecastPosition && uncertaintyKm) {
        L.circle(
          [
            forecastPosition.latitude,
            forecastPosition.longitude,
          ],
          {
            radius: uncertaintyKm * 1000,
            weight: 1,
            fillOpacity: 0.08,
          }
        ).addTo(map);
      }

      /*
       * Current iceberg
       */
      const icebergMarker = L.circleMarker(
        [
          currentPosition.latitude,
          currentPosition.longitude,
        ],
        {
          radius: 9,
          weight: 2,
          fillOpacity: 0.15,
        }
      ).addTo(map);

      icebergMarker.bindTooltip("ICEBERG D29C", {
        permanent: true,
        direction: "top",
        offset: [0, -8],
      });

      /*
       * Automatically frame the mission after
       * a calculated route becomes available.
       */
      const recommendedRoute =
        recommendedProfile === "safest"
          ? routes?.safest
          : recommendedProfile === "balanced"
            ? routes?.balanced
            : recommendedProfile === "fuel"
              ? routes?.fuel
              : undefined;

      if (recommendedRoute?.geometry?.length) {
        const boundsPoints = [
          [
            vesselPosition.latitude,
            vesselPosition.longitude,
          ] as [number, number],

          [
            destinationPosition.latitude,
            destinationPosition.longitude,
          ] as [number, number],

          ...recommendedRoute.geometry.map(
            (point) =>
              [point.latitude, point.longitude] as [
                number,
                number
              ]
          ),
        ];

        const bounds = L.latLngBounds(boundsPoints);

        map.fitBounds(bounds, {
          padding: [50, 50],
          maxZoom: 7,
        });
      }

      /*
       * Fix map dimensions after mounting.
       */
      requestAnimationFrame(() => {
        map.invalidateSize();
      });
    }

    initializeMap();

    return () => {
      cancelled = true;

      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [
    currentPosition,
    vesselPosition,
    destinationPosition,
    forecastPosition,
    uncertaintyKm,
    routes,
    recommendedProfile,
  ]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{
        width: "100%",
        height: "100%",
        minHeight: "500px",
        zIndex: 0,
        pointerEvents: "auto",
      }}
    />
  );
}