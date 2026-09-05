import { Snowflake } from "lucide-react";
import type { ForecastResponse } from "../types";

interface IcebergState {
  lat: string;
  lon: string;
  status: string;
}

interface IcebergPanelProps {
  selectedHour: number;
  icebergState: IcebergState;
  forecast: ForecastResponse | null;
  cpaKm?: number | null;
  selectedIcebergId: string;
}

export default function IcebergPanel({
  selectedHour,
  icebergState,
  forecast,
  cpaKm,
  selectedIcebergId,
}: IcebergPanelProps)  {
  const selectedTrajectoryPoint =
    selectedHour > 0
      ? forecast?.trajectory?.find(
          (point) => point.hours === selectedHour
        )
      : undefined;

  const displayedLatitude =
    selectedTrajectoryPoint?.latitude ?? icebergState.lat;

  const displayedLongitude =
    selectedTrajectoryPoint?.longitude ?? icebergState.lon;

  return (
    <>
      <SectionTitle
  title={`ICEBERG ${selectedIcebergId.toUpperCase()}`}
/>

      <div className="px-5 py-4">
        <div className="grid grid-cols-2 gap-y-4">
          <Data
            label="POSITION"
            value={
              typeof displayedLatitude === "number"
                ? `${Math.abs(displayedLatitude).toFixed(3)}° S`
                : displayedLatitude
            }
          />

          <Data
            label="LONGITUDE"
            value={
              typeof displayedLongitude === "number"
                ? `${Math.abs(displayedLongitude).toFixed(3)}° W`
                : displayedLongitude
            }
          />

          <Data
            label="DRIFT SPEED"
            value={
              forecast
                ? `${forecast.forecast.speed_kmh.toFixed(2)} km/h`
                : "—"
            }
          />

          <Data
            label="HEADING"
            value={
              forecast
                ? `${forecast.forecast.heading_deg
                    .toFixed(1)
                    .padStart(5, "0")}°`
                : "—"
            }
          />

          <Data
            label="UNCERTAINTY"
            value={
              forecast
                ? `${forecast.ensemble.uncertainty_radius_km.toFixed(2)} km`
                : "—"
            }
          />

          <Data
            label="CPA"
            value={
              cpaKm != null
                ? `${cpaKm.toFixed(2)} km`
                : "—"
            }
          />
        </div>
      </div>

      {/* Forecast trajectory */}
      {forecast?.trajectory?.length ? (
        <div className="border-y border-[#cdd2cf] bg-[#fafbfa] px-5 py-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[9px] tracking-[0.15em] text-[#687579]">
              DRIFT TRAJECTORY
            </span>

            <span className="font-mono text-[9px] text-[#365e72]">
              24H MODEL
            </span>
          </div>

          <div className="space-y-2">
            {forecast.trajectory.map((point) => (
              <div
                key={point.hours}
                className={`grid grid-cols-[42px_1fr_1fr] items-center gap-3 font-mono text-[9px] ${
                  selectedHour === point.hours
                    ? "font-semibold text-[#1f4f63]"
                    : "text-[#687579]"
                }`}
              >
                <span>+{point.hours}H</span>

                <span>
                  {Math.abs(point.latitude).toFixed(3)}° S
                </span>

                <span>
                  {Math.abs(point.longitude).toFixed(3)}° W
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="border-y border-[#cdd2cf] bg-[#f4f6f5] px-5 py-4">
        <div className="flex items-center justify-between">
          <span className="text-[9px] tracking-[0.15em] text-[#687579]">
            TEMPORAL STATE
          </span>

          <span className="font-mono text-[9px] text-[#365e72]">
            {icebergState.status}
          </span>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <Data
            label="SELECTED TIME"
            value={
              selectedHour === 0
                ? "NOW"
                : `${selectedHour > 0 ? "+" : ""}${selectedHour}h`
            }
          />

          <Data
            label="DATA TYPE"
            value={
              selectedHour <= 0
                ? "OBSERVED"
                : "FORECAST"
            }
          />
        </div>
      </div>

      <div className="border-b border-[#cdd2cf] bg-[#f7eeee] px-5 py-4">
        <div className="flex items-center gap-2 text-[#a84d43]">
          <Snowflake size={15} />

          <span className="text-[11px] font-semibold tracking-wider">
            ROUTE HAZARD
          </span>
        </div>

        <p className="mt-2 text-[11px] leading-relaxed text-[#5d4a47]">
          Predicted iceberg trajectory enters the operational route
          corridor.
        </p>
      </div>
    </>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div className="border-b border-[#cdd2cf] px-5 py-3 text-[10px] font-semibold tracking-[0.16em] text-[#59666a]">
      {title}
    </div>
  );
}

function Data({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-[9px] text-[#7a8588]">
        {label}
      </div>

      <div className="mt-1 font-mono text-[11px]">
        {value}
      </div>
    </div>
  );
}