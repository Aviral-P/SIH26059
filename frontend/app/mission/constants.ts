export const routes = [
  {
    name: "Safest",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "4.57 km",
    selected: true,
  },
  {
    name: "Balanced",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "4.57 km",
    selected: false,
  },
  {
    name: "Fuel optimized",
    distance: "61.7 km",
    eta: "3h 20m",
    risk: "HIGH",
    cpa: "0.00 km",
    selected: false,
  },
];

export const timeOptions = [
  { hour: -24, label: "−24h", type: "PAST" },
  { hour: -12, label: "−12h", type: "PAST" },
  { hour: 0, label: "NOW", type: "CURRENT" },
  { hour: 6, label: "+6h", type: "FORECAST" },
  { hour: 12, label: "+12h", type: "FORECAST" },
  { hour: 24, label: "+24h", type: "FORECAST" },
];

export const icebergTimeline = {
  [-24]: {
    lat: "63.388 S",
    lon: "47.554 W",
    status: "OBSERVED",
  },
  [-12]: {
    lat: "63.356 S",
    lon: "47.412 W",
    status: "OBSERVED",
  },
  [0]: {
    lat: "63.314 S",
    lon: "47.283 W",
    status: "CURRENT",
  },
  [6]: {
    lat: "63.267 S",
    lon: "47.126 W",
    status: "FORECAST",
  },
  [12]: {
    lat: "63.220 S",
    lon: "46.967 W",
    status: "FORECAST",
  },
  [24]: {
    lat: "63.126 S",
    lon: "46.653 W",
    status: "FORECAST",
  },
} as const;

/*
 * D29C trajectory positions used by the current prototype map.
 *
 * The latitude/longitude values are represented in icebergTimeline.
 * These x/y values are only the visual projection into the current
 * SVG chart and are not geographic coordinates.
 */
export function getIcebergMapPosition(hour: number) {
  const positions = {
    [-24]: { x: 360, y: 300 },
    [-12]: { x: 390, y: 280 },
    [0]: { x: 430, y: 255 },
    [6]: { x: 465, y: 235 },
    [12]: { x: 500, y: 215 },
    [24]: { x: 550, y: 185 },
  };

  return positions[hour as keyof typeof positions] ?? positions[0];
}

export const icebergTrajectory = [
  { hour: -24, x: 360, y: 300 },
  { hour: -12, x: 390, y: 280 },
  { hour: 0, x: 430, y: 255 },
  { hour: 6, x: 465, y: 235 },
  { hour: 12, x: 500, y: 215 },
  { hour: 24, x: 550, y: 185 },
];