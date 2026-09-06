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
  points: RouteGeometryPoint[];
}

interface MissionRoutes {
  safest?: MissionRoute;
  balanced?: MissionRoute;
  fuel_optimized?: MissionRoute;
}

interface SeaIceCell {
  latitude: number;
  longitude: number;
  concentration: number;
}

interface IcebergObservation {
  iceberg_id: string;
  observed_at: string;
  latitude: number;
  longitude: number;
  displacement_km: number | null;
  velocity_kmh: number | null;
  velocity_angle_deg: number | null;
}

interface MissionMapProps {
  currentPosition: Position;
  vesselPosition: Position;
  destination: Position;

  forecastPosition?: Position;
  uncertaintyKm?: number;

  trajectory?: Array<{
    hours: number;
    latitude: number;
    longitude: number;
  }>;

  routes?: MissionRoutes;
  recommendedProfile?: string;
  riskLevel?: string;
  riskCpaKm?: number;

  trajectoryStartPosition?: Position;

  seaIce?: SeaIceCell[];

  icebergs?: IcebergObservation[];

  selectedIcebergId?: string;

  onIcebergSelect?: (icebergId: string) => void;

  layerVisibility?: {
    seaIce: boolean;
    icebergs: boolean;
    routes: boolean;
    forecast: boolean;
    riskZones: boolean;
  };
}

export default function MissionMap({
  currentPosition,
  vesselPosition,
  destination,
  forecastPosition,
  uncertaintyKm,
  trajectory,
  routes,
  recommendedProfile,
  riskLevel,
  riskCpaKm,
  trajectoryStartPosition,
  seaIce,
  icebergs,
  selectedIcebergId,
  onIcebergSelect,
  layerVisibility,
}: MissionMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const mapRef = useRef<import("leaflet").Map | null>(null);

  const layersRef = useRef<import("leaflet").LayerGroup[]>([]);

  const leafletRef = useRef<typeof import("leaflet") | null>(null);

  /*
   * ==================================================
   * MAP LAYER VISIBILITY
   * ==================================================
   *
   * These are real Leaflet analytical layers.
   * Core navigation references (vessel/destination/
   * tracked iceberg) remain visible at all times.
   */
  const layerVisibilityRef = useRef({
    seaIce: layerVisibility?.seaIce ?? true,
    icebergs: layerVisibility?.icebergs ?? true,
    routes: layerVisibility?.routes ?? true,
    forecast: layerVisibility?.forecast ?? true,
    riskZones: layerVisibility?.riskZones ?? true,
  });

  /*
   * Keep the latest props available to the single
   * Leaflet lifecycle.
   */
  const propsRef = useRef({
    currentPosition,
    vesselPosition,
    destination,
    forecastPosition,
    uncertaintyKm,
    trajectory,
    routes,
    recommendedProfile,
    riskLevel,
    riskCpaKm,
    trajectoryStartPosition,
    seaIce,
    icebergs,
    selectedIcebergId,
    onIcebergSelect,
  });

  propsRef.current = {
    currentPosition,
    vesselPosition,
    destination,
    forecastPosition,
    uncertaintyKm,
    trajectory,
    routes,
    recommendedProfile,
    riskLevel,
    riskCpaKm,
    trajectoryStartPosition,
    seaIce,
    icebergs,
    selectedIcebergId,
    onIcebergSelect,
  };

  /*
   * ==================================================
   * MAP INITIALIZATION
   * ==================================================
   *
   * Leaflet is initialized exactly once.
   *
   * The map itself is NOT destroyed/recreated whenever
   * application state changes.
   */

  useEffect(() => {
    let cancelled = false;

    async function initializeMap() {
      if (!containerRef.current || mapRef.current) {
        return;
      }

      const L = await import("leaflet");

      if (cancelled || !containerRef.current || mapRef.current) {
        return;
      }

      leafletRef.current = L;

      const { currentPosition } = propsRef.current;

      const map = L.map(containerRef.current, {
        center: [currentPosition.latitude, currentPosition.longitude],

        zoom: 4,
        minZoom: 2,
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        dragging: true,
        touchZoom: true,
        boxZoom: true,
        keyboard: true,

        // Keep vertical movement inside the real Web-Mercator world.
        maxBounds: [
          [-85.05112878, -Infinity],
          [85.05112878, Infinity],
        ],
        maxBoundsViscosity: 1.0,
      });

      /*
       * Store map reference immediately.
       */
      mapRef.current = map;

      /*
       * ==================================================
       * OPENSTREETMAP
       * ==================================================
       */

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);

      /*
       * ==================================================
       * SEA ICE LEGEND
       * ==================================================
       */

      const seaIceLegend = new L.Control({
        position: "bottomright",
      });

      seaIceLegend.onAdd = () => {
        const div = L.DomUtil.create(
          "div",
          "bg-white/95 border border-[#cdd2cf] px-3 py-2 shadow-sm",
        );

        div.innerHTML = `
          <div style="
            font-size:9px;
            letter-spacing:0.12em;
            color:#59666a;
            margin-bottom:6px;
          ">
            SEA ICE CONCENTRATION
          </div>

          <div style="
            display:flex;
            align-items:center;
            gap:6px;
            font-size:9px;
            color:#687579;
            margin-bottom:3px;
          ">
            <span style="
              width:12px;
              height:10px;
              background:#7f9eaa;
              opacity:0.12;
              display:inline-block;
            "></span>
            0–20%
          </div>

          <div style="
            display:flex;
            align-items:center;
            gap:6px;
            font-size:9px;
            color:#687579;
            margin-bottom:3px;
          ">
            <span style="
              width:12px;
              height:10px;
              background:#7f9eaa;
              opacity:0.20;
              display:inline-block;
            "></span>
            20–50%
          </div>

          <div style="
            display:flex;
            align-items:center;
            gap:6px;
            font-size:9px;
            color:#687579;
            margin-bottom:3px;
          ">
            <span style="
              width:12px;
              height:10px;
              background:#7f9eaa;
              opacity:0.32;
              display:inline-block;
            "></span>
            50–80%
          </div>

          <div style="
            display:flex;
            align-items:center;
            gap:6px;
            font-size:9px;
            color:#687579;
          ">
            <span style="
              width:12px;
              height:10px;
              background:#7f9eaa;
              opacity:0.48;
              display:inline-block;
            "></span>
            80–100%
          </div>
        `;

        return div;
      };

      seaIceLegend.addTo(map);

      /*
       * Initial data rendering.
       */
      renderLayers(L, map);

      requestAnimationFrame(() => {
        if (!cancelled && mapRef.current) {
          mapRef.current.invalidateSize();
        }
      });
    }

    initializeMap();

    return () => {
      cancelled = true;

      /*
       * Remove dynamic layers first.
       */
      layersRef.current.forEach((layer) => {
        try {
          layer.remove();
        } catch {
          // Ignore already-removed Leaflet layers.
        }
      });

      layersRef.current = [];

      /*
       * Remove Leaflet map exactly once.
       */
      if (mapRef.current) {
        try {
          mapRef.current.remove();
        } catch {
          // Ignore Leaflet cleanup errors during hot reload.
        }

        mapRef.current = null;
      }

      leafletRef.current = null;
    };

    // IMPORTANT:
    // The Leaflet map lifecycle intentionally runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /*
   * ==================================================
   * CONTROLLED LAYER VISIBILITY
   * ==================================================
   *
   * React owns the layer switches. Leaflet only renders
   * the resulting analytical layers.
   */

  useEffect(() => {
    if (!layerVisibility) return;

    layerVisibilityRef.current = {
      seaIce: layerVisibility.seaIce,
      icebergs: layerVisibility.icebergs,
      routes: layerVisibility.routes,
      forecast: layerVisibility.forecast,
      riskZones: layerVisibility.riskZones,
    };

    const L = leafletRef.current;
    const map = mapRef.current;

    if (L && map) {
      renderLayers(L, map);
    }
  }, [
    layerVisibility?.seaIce,
    layerVisibility?.icebergs,
    layerVisibility?.routes,
    layerVisibility?.forecast,
    layerVisibility?.riskZones,
  ]);

  /*
   * ==================================================
   * DYNAMIC LAYERS
   * ==================================================
   *
   * Re-render data without recreating the Leaflet map.
   */

  useEffect(() => {
    const L = leafletRef.current;
    const map = mapRef.current;

    if (!L || !map) {
      return;
    }

    renderLayers(L, map);
  }, [
    currentPosition,
    vesselPosition,
    destination,
    forecastPosition,
    uncertaintyKm,
    trajectory,
    routes,
    recommendedProfile,
    riskLevel,
    riskCpaKm,
    trajectoryStartPosition,
    seaIce,
    icebergs,
    selectedIcebergId,
    onIcebergSelect,
  ]);

  /*
   * ==================================================
   * RENDER DYNAMIC LAYERS
   * ==================================================
   */

  function renderLayers(
    L: typeof import("leaflet"),
    map: import("leaflet").Map,
  ) {
    /*
     * Remove previous dynamic layers.
     *
     * The base OSM layer and map instance remain alive.
     */

    layersRef.current.forEach((layer) => {
      try {
        layer.remove();
      } catch {
        // Ignore already-removed layers.
      }
    });

    layersRef.current = [];

    const {
      currentPosition,
      vesselPosition,
      destination,
      forecastPosition,
      uncertaintyKm,
      trajectory,
      routes,
      recommendedProfile,
      riskLevel,
      riskCpaKm,
      trajectoryStartPosition,
      seaIce,
      icebergs,
      selectedIcebergId,
      onIcebergSelect,
    } = propsRef.current;

    /*
     * ==================================================
     * SEA ICE
     * ==================================================
     */

    if (layerVisibilityRef.current.seaIce && seaIce && seaIce.length > 0) {
      const seaIceLayer = L.layerGroup().addTo(map);

      seaIce.forEach((cell) => {
        const concentration = Math.max(0, Math.min(1, cell.concentration));

        let fillOpacity = 0.12;

        if (concentration >= 0.8) {
          fillOpacity = 0.48;
        } else if (concentration >= 0.5) {
          fillOpacity = 0.32;
        } else if (concentration >= 0.2) {
          fillOpacity = 0.2;
        }

        /*
         * NSIDC grid is 25 km.
         *
         * This circle is only a visual footprint
         * around the cell centre.
         */

        const cellRadiusKm = 12.5;

        L.circle([cell.latitude, cell.longitude], {
          radius: cellRadiusKm * 1000,
          stroke: false,
          fillOpacity,
          fillColor: "#7f9eaa",
        })
          .bindTooltip(`SEA ICE ${(concentration * 100).toFixed(1)}%`, {
            direction: "top",
            offset: [0, -6],
          })
          .addTo(seaIceLayer);
      });

      layersRef.current.push(seaIceLayer);
    }

    /*
     * ==================================================
     * REAL ICEBERG OBSERVATIONS
     * ==================================================
     */

    if (
      layerVisibilityRef.current.icebergs &&
      icebergs &&
      icebergs.length > 0
    ) {
      const latestIcebergs = new Map<string, IcebergObservation>();

      icebergs.forEach((iceberg) => {
        const existing = latestIcebergs.get(iceberg.iceberg_id);

        if (
          !existing ||
          new Date(iceberg.observed_at).getTime() >
            new Date(existing.observed_at).getTime()
        ) {
          latestIcebergs.set(iceberg.iceberg_id, iceberg);
        }
      });

      const icebergLayer = L.layerGroup().addTo(map);

      latestIcebergs.forEach((iceberg) => {
        const isSelected = iceberg.iceberg_id === selectedIcebergId;

        const marker = L.circleMarker([iceberg.latitude, iceberg.longitude], {
          radius: isSelected ? 9 : 5,

          weight: isSelected ? 2.5 : 1.5,

          fillOpacity: isSelected ? 0.25 : 0.85,

          fillColor: "#ffffff",
        });

        marker.on("click", () => {
          onIcebergSelect?.(iceberg.iceberg_id);
        });

        marker.bindTooltip(
          isSelected
            ? `SELECTED • ICEBERG ${iceberg.iceberg_id}`
            : `ICEBERG ${iceberg.iceberg_id}`,
          {
            direction: "top",
            offset: [0, -6],
          },
        );

        marker.bindPopup(`
          <div style="
            min-width:170px;
            font-family:Arial,sans-serif;
            font-size:11px;
            line-height:1.6;
          ">

            <div style="
              font-weight:600;
              font-size:12px;
              margin-bottom:5px;
            ">
              ICEBERG ${iceberg.iceberg_id}
            </div>

            <div>
              <strong>Observed</strong><br/>
              ${iceberg.observed_at}
            </div>

            <div style="
              margin-top:4px;
            ">
              <strong>Position</strong><br/>
              ${iceberg.latitude.toFixed(3)}°,
              ${iceberg.longitude.toFixed(3)}°
            </div>

            <div style="
              margin-top:5px;
              color:#687579;
              font-size:9px;
            ">
              SOURCE: BYU / NIC TRACK DATABASE
            </div>

          </div>
        `);

        marker.addTo(icebergLayer);
      });

      layersRef.current.push(icebergLayer);
    }

    /*
     * ==================================================
     * ROUTES
     * ==================================================
     */

    const drawRoute = (
      route: MissionRoute | undefined,
      options: import("leaflet").PolylineOptions,
      label: string,
      targetLayer: import("leaflet").LayerGroup,
    ) => {
      if (!route || !route.points || route.points.length === 0) {
        return;
      }

      const points = route.points.map(
        (point) => [point.latitude, point.longitude] as [number, number],
      );

      const line = L.polyline(points, options).addTo(targetLayer);

      line.bindTooltip(label.toUpperCase(), {
        sticky: true,
        direction: "top",
      });
    };

    const routeLayer = L.layerGroup();

    if (layerVisibilityRef.current.routes) {
      routeLayer.addTo(map);
    }

    const routeStyles = {
      safest: {
        color: "#365e72",
        weight: 3,
        opacity: 0.55,
        dashArray: "8 6",
        lineCap: "round" as const,
        lineJoin: "round" as const,
      },

      balanced: {
        color: "#6d7d82",
        weight: 3,
        opacity: 0.6,
        dashArray: "3 5",
        lineCap: "round" as const,
        lineJoin: "round" as const,
      },

      fuel: {
        color: "#876d3f",
        weight: 3,
        opacity: 0.55,
        dashArray: "2 8",
        lineCap: "round" as const,
        lineJoin: "round" as const,
      },
    };

    const recommendedStyle = {
      color: "#263337",
      weight: 5,
      opacity: 0.95,
      lineCap: "round" as const,
      lineJoin: "round" as const,
    };

    drawRoute(
      routes?.safest,
      recommendedProfile === "safest" ? recommendedStyle : routeStyles.safest,
      "SAFEST ROUTE",
      routeLayer,
    );

    drawRoute(
      routes?.balanced,
      recommendedProfile === "balanced"
        ? recommendedStyle
        : routeStyles.balanced,
      "BALANCED ROUTE",
      routeLayer,
    );

    drawRoute(
      routes?.fuel_optimized,
      recommendedProfile === "fuel_optimized"
        ? recommendedStyle
        : routeStyles.fuel,
      "FUEL OPTIMIZED ROUTE",
      routeLayer,
    );

    if (
      layerVisibilityRef.current.routes &&
      (routes?.safest || routes?.balanced || routes?.fuel_optimized)
    ) {
      layersRef.current.push(routeLayer);
    } else {
      routeLayer.remove();
    }

    /*
     * ==================================================
     * ICEBERG FORECAST TRAJECTORY
     * ==================================================
     */

    if (
      layerVisibilityRef.current.forecast &&
      trajectory &&
      trajectory.length > 0
    ) {
      const trajectoryLayer = L.layerGroup().addTo(map);

      const trajectoryStart = trajectoryStartPosition ?? currentPosition;

      const trajectoryPoints: [number, number][] = [
        [trajectoryStart.latitude, trajectoryStart.longitude],

        ...trajectory.map(
          (point) => [point.latitude, point.longitude] as [number, number],
        ),
      ];

      L.polyline(trajectoryPoints, {
        weight: 3,
        opacity: 0.9,
        dashArray: "8 6",
      }).addTo(trajectoryLayer);

      trajectory.forEach((point) => {
        L.circleMarker([point.latitude, point.longitude], {
          radius: 4,
          weight: 1,
          fillOpacity: 1,
        })
          .bindTooltip(`ICEBERG +${point.hours}H`, {
            direction: "top",
            offset: [0, -6],
          })
          .addTo(trajectoryLayer);
      });

      layersRef.current.push(trajectoryLayer);
    }

    /*
     * ==================================================
     * OPERATIONAL ICEBERG RISK ZONE
     * ==================================================
     *
     * This is a proximity/hazard visualization derived
     * from the route evaluator's risk level.
     *
     * It is NOT a probabilistic collision footprint.
     *
     * HIGH   -> 5 km operational proximity zone
     * MEDIUM -> 15 km operational proximity zone
     * LOW    -> no zone
     */

    const normalizedRisk =
      riskLevel?.replaceAll("_", " ").toUpperCase() ?? "LOW";

    const riskZoneRadiusKm =
      normalizedRisk === "HIGH" ? 5 : normalizedRisk === "MEDIUM" ? 15 : 15;

    if (layerVisibilityRef.current.riskZones) {
      const riskZoneLayer = L.layerGroup().addTo(map);

      const riskZone = L.circle(
        [currentPosition.latitude, currentPosition.longitude],
        {
          radius: riskZoneRadiusKm * 1000,

          color:
            normalizedRisk === "HIGH"
              ? "#a84d43"
              : normalizedRisk === "MEDIUM"
                ? "#876d3f"
                : "#718087",

          weight: normalizedRisk === "LOW" ? 1 : 1.5,
          opacity: normalizedRisk === "LOW" ? 0.45 : 0.8,

          dashArray: "6 5",

          fillColor:
            normalizedRisk === "HIGH"
              ? "#a84d43"
              : normalizedRisk === "MEDIUM"
                ? "#876d3f"
                : "#718087",

          fillOpacity:
            normalizedRisk === "HIGH"
              ? 0.1
              : normalizedRisk === "MEDIUM"
                ? 0.07
                : 0.025,
        },
      ).addTo(riskZoneLayer);

      riskZone.bindTooltip(
        `${normalizedRisk} ICEBERG PROXIMITY ZONE • ${riskZoneRadiusKm} km`,
        {
          direction: "top",
          sticky: true,
        },
      );

      if (riskCpaKm !== undefined && Number.isFinite(riskCpaKm)) {
        riskZone.bindPopup(`
      <div style="
        min-width:170px;
        font-family:Arial,sans-serif;
        font-size:11px;
        line-height:1.6;
      ">
        <div style="
          font-weight:600;
          font-size:12px;
          margin-bottom:5px;
        ">
          ${normalizedRisk} ROUTE HAZARD
        </div>

        <div>
          <strong>Operational zone</strong><br/>
          ${riskZoneRadiusKm} km radius
        </div>

        <div style="margin-top:4px;">
          <strong>Minimum route separation</strong><br/>
          ${riskCpaKm.toFixed(2)} km
        </div>

        <div style="
          margin-top:6px;
          color:#687579;
          font-size:9px;
        ">
          PROXIMITY INDICATOR — NOT A COLLISION PROBABILITY
        </div>
      </div>
    `);
      }

      layersRef.current.push(riskZoneLayer);
    }

    /*
     * ==================================================
     * VESSEL
     * ==================================================
     */

    const vesselLayer = L.layerGroup().addTo(map);

    const vesselMarker = L.circleMarker(
      [vesselPosition.latitude, vesselPosition.longitude],
      {
        radius: 7,
        weight: 2,
      },
    ).addTo(vesselLayer);

    vesselMarker.bindTooltip("VESSEL", {
      permanent: true,
      direction: "bottom",
      offset: [0, 8],
    });

    /*
     * ==================================================
     * DESTINATION
     * ==================================================
     */

    const destinationMarker = L.circleMarker(
      [destination.latitude, destination.longitude],
      {
        radius: 7,
        weight: 2,
        fillOpacity: 0.15,
      },
    ).addTo(vesselLayer);

    destinationMarker.bindTooltip("DESTINATION", {
      permanent: true,
      direction: "top",
      offset: [0, -8],
    });

    /*
     * ==================================================
     * +24H FORECAST
     * ==================================================
     */

    if (forecastPosition) {
      L.circleMarker([forecastPosition.latitude, forecastPosition.longitude], {
        radius: 5,
        weight: 2,
      })
        .bindTooltip("+24H FORECAST", {
          permanent: true,
          direction: "bottom",
          offset: [0, 8],
        })
        .addTo(vesselLayer);
    }

    /*
     * ==================================================
     * UNCERTAINTY
     * ==================================================
     */

    if (forecastPosition && uncertaintyKm !== undefined && uncertaintyKm > 0) {
      L.circle([forecastPosition.latitude, forecastPosition.longitude], {
        radius: uncertaintyKm * 1000,

        weight: 1,

        fillOpacity: 0.08,
      }).addTo(vesselLayer);
    }

    /*
     * ==================================================
     * TRACKED / SELECTED ICEBERG
     * ==================================================
     */

    const trackedIcebergMarker = L.circleMarker(
      [currentPosition.latitude, currentPosition.longitude],
      {
        radius: 9,
        weight: 2,
        fillOpacity: 0.15,
      },
    ).addTo(vesselLayer);

    trackedIcebergMarker.bindTooltip(
      selectedIcebergId
        ? `TRACKED ICEBERG ${selectedIcebergId}`
        : "TRACKED ICEBERG",
      {
        permanent: true,
        direction: "top",
        offset: [0, -8],
      },
    );

    layersRef.current.push(vesselLayer);

    /*
     * ==================================================
     * FIT MAP TO RECOMMENDED ROUTE
     * ==================================================
     */

    const recommendedRoute =
      recommendedProfile === "safest"
        ? routes?.safest
        : recommendedProfile === "balanced"
          ? routes?.balanced
          : recommendedProfile === "fuel_optimized"
            ? routes?.fuel_optimized
            : undefined;

    if (
      recommendedRoute &&
      recommendedRoute.points &&
      recommendedRoute.points.length > 0
    ) {
      const boundsPoints: [number, number][] = [
        [vesselPosition.latitude, vesselPosition.longitude],

        [destination.latitude, destination.longitude],

        ...recommendedRoute.points.map(
          (point) => [point.latitude, point.longitude] as [number, number],
        ),
      ];

      const bounds = L.latLngBounds(boundsPoints);

      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 7,
      });
    }

    /*
     * Leaflet sometimes needs an explicit size refresh
     * after being mounted inside a grid/flex layout.
     */

    requestAnimationFrame(() => {
      if (mapRef.current === map) {
        map.invalidateSize();
      }
    });
  }

  /*
   * ==================================================
   * MAP CONTAINER
   * ==================================================
   */

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
