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
}

export default function IcebergPanel({
  selectedHour,
  icebergState,
  forecast,
  cpaKm,
}: IcebergPanelProps) {
  return (
    <>
      <SectionTitle title="ICEBERG D29C" />

      <div className="px-5 py-4">
        <div className="grid grid-cols-2 gap-y-4">
          <Data
            label="POSITION"
            value={
              selectedHour === 24 && forecast
                ? `${Math.abs(forecast.forecast.latitude).toFixed(3)}° S`
                : icebergState.lat
            }
          />

          <Data
            label="LONGITUDE"
            value={
              selectedHour === 24 && forecast
                ? `${Math.abs(forecast.forecast.longitude).toFixed(3)}° W`
                : icebergState.lon
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
            value={selectedHour <= 0 ? "OBSERVED" : "FORECAST"}
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