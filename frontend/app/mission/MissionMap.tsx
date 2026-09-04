"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Global CSS to ensure MapLibre interactions work
// This must run once per app, not per component
if (
  typeof document !== "undefined" &&
  !document.getElementById("maplibre-interaction-fix")
) {
  const style = document.createElement("style");
  style.id = "maplibre-interaction-fix";
  style.textContent = `
    /* Ensure MapLibre canvas receives all pointer events */
    .maplibregl-canvas {
      pointer-events: auto !important;
      touch-action: none !important;
    }

    /* Ensure MapLibre controls are clickable */
    .maplibregl-ctrl {
      pointer-events: auto !important;
    }

    .maplibregl-ctrl-group button {
      pointer-events: auto !important;
      cursor: pointer;
    }

    /* Ensure navigation control buttons work */
    .maplibregl-ctrl-zoom-in,
    .maplibregl-ctrl-zoom-out {
      pointer-events: auto !important;
      cursor: pointer !important;
    }

    /* Ensure popups are clickable */
    .maplibregl-popup {
      pointer-events: auto !important;
    }

    .maplibregl-popup-content {
      pointer-events: auto !important;
    }
  `;
  document.head.appendChild(style);
}

interface Position {
  latitude: number;
  longitude: number;
}

interface MissionMapProps {
  currentPosition: Position;
  forecastPosition?: Position;
  uncertaintyKm?: number;
}

export default function MissionMap({
  currentPosition,
  forecastPosition,
  uncertaintyKm = 0,
}: MissionMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    const container = containerRef.current;

    if (!container || mapRef.current) return;

    const map = new maplibregl.Map({
      container,
      style: "https://demotiles.maplibre.org/style.json",

      center: [currentPosition.longitude, currentPosition.latitude],

      zoom: 3.5,

      attributionControl: false,

      // Navigation
      scrollZoom: true,
      dragPan: true,
      dragRotate: false,
      doubleClickZoom: true,
      boxZoom: true,
      keyboard: true,
      touchZoomRotate: true,

      // Make sure the map can receive pointer input
      interactive: true,
    });

    mapRef.current = map;

    /*
     * NAVIGATION CONTROLS
     */
    map.addControl(
      new maplibregl.NavigationControl({
        showCompass: false,
        showZoom: true,
      }),
      "top-right",
    );

    /*
     * DEBUG — proves MapLibre receives wheel input
     */
    const handleWheel = () => {
      console.log("MAP WHEEL EVENT");
    };

    container.addEventListener("wheel", handleWheel, {
      passive: true,
    });

    /*
     * MAP LOAD
     */
    map.on("load", () => {
      console.log("MAP LOADED — scroll:", map.scrollZoom.isEnabled());

      console.log("MAP LOADED — drag:", map.dragPan.isEnabled());

      /*
       * Explicitly enable every interaction
       */
      map.scrollZoom.enable();
      map.dragPan.enable();
      map.doubleClickZoom.enable();
      map.boxZoom.enable();
      map.keyboard.enable();
      map.touchZoomRotate.enable();

      /*
       * CURRENT ICEBERG
       */
      new maplibregl.Marker({
        color: "#a84d43",
      })
        .setLngLat([currentPosition.longitude, currentPosition.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(`
            <div style="font-family:sans-serif">
              <strong>D29C</strong><br/>
              Current Position<br/>
              <small>
                ${currentPosition.latitude.toFixed(3)},
                ${currentPosition.longitude.toFixed(3)}
              </small>
            </div>
          `),
        )
        .addTo(map);

      /*
       * FORECAST POSITION
       */
      if (forecastPosition) {
        new maplibregl.Marker({
          color: "#365e72",
        })
          .setLngLat([forecastPosition.longitude, forecastPosition.latitude])
          .setPopup(
            new maplibregl.Popup({ offset: 25 }).setHTML(`
              <div style="font-family:sans-serif">
                <strong>D29C · +24H</strong><br/>
                Forecast Position<br/>
                <small>
                  ${forecastPosition.latitude.toFixed(3)},
                  ${forecastPosition.longitude.toFixed(3)}
                </small>
              </div>
            `),
          )
          .addTo(map);

        /*
         * PREDICTED TRAJECTORY
         */
        map.addSource("iceberg-trajectory", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: {
              type: "LineString",
              coordinates: [
                [currentPosition.longitude, currentPosition.latitude],
                [forecastPosition.longitude, forecastPosition.latitude],
              ],
            },
          },
        });

        map.addLayer({
          id: "iceberg-trajectory-line",
          type: "line",
          source: "iceberg-trajectory",
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
          paint: {
            "line-color": "#365e72",
            "line-width": 3,
            "line-dasharray": [2, 2],
            "line-opacity": 0.9,
          },
        });
      }

      /*
       * FORECAST UNCERTAINTY
       */
      if (forecastPosition && uncertaintyKm > 0) {
        const radiusDegrees = uncertaintyKm / 111;

        const points: [number, number][] = [];

        for (let i = 0; i <= 64; i++) {
          const angle = (i / 64) * Math.PI * 2;

          points.push([
            forecastPosition.longitude + radiusDegrees * Math.cos(angle),

            forecastPosition.latitude + radiusDegrees * Math.sin(angle),
          ]);
        }

        map.addSource("forecast-uncertainty", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: {
              type: "Polygon",
              coordinates: [points],
            },
          },
        });

        map.addLayer({
          id: "forecast-uncertainty-fill",
          type: "fill",
          source: "forecast-uncertainty",
          paint: {
            "fill-color": "#365e72",
            "fill-opacity": 0.08,
          },
        });

        map.addLayer({
          id: "forecast-uncertainty-outline",
          type: "line",
          source: "forecast-uncertainty",
          paint: {
            "line-color": "#365e72",
            "line-width": 1.5,
            "line-opacity": 0.5,
          },
        });
      }

      /*
       * VESSEL
       */
      new maplibregl.Marker({
        color: "#263238",
      })
        .setLngLat([-47.85, -63.55])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(`
            <div style="font-family:sans-serif">
              <strong>RV POLARIS</strong><br/>
              Mission Vessel
            </div>
          `),
        )
        .addTo(map);

      /*
       * Make sure the map fills its container
       */
      requestAnimationFrame(() => {
        map.resize();
      });
    });

    /*
     * MAP ERROR
     */
    map.on("error", (event) => {
      console.error("MAPLIBRE ERROR:", event);
    });

    /*
     * CLEANUP
     */
    return () => {
      container.removeEventListener("wheel", handleWheel);

      map.remove();

      mapRef.current = null;
    };
  }, [currentPosition, forecastPosition, uncertaintyKm]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        inset: "0px",
        width: "100%",
        height: "100%",
        minHeight: "500px",

        /*
         * CRITICAL: Inline styles take precedence over Tailwind classes
         * Ensure map canvas receives all pointer events
         */
        pointerEvents: "auto",

        /*
         * Prevent browser default touch gestures from interfering
         * with MapLibre interactions
         */
        touchAction: "none",

        /* Ensure no background images or colors hide the map */
        background: "transparent",
        zIndex: 0,
      }}
    />
  );
}
