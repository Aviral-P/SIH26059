"use client";

import { Crosshair, Ship, X } from "lucide-react";

interface MissionControlsProps {
  origin: { latitude: number; longitude: number };
  destination: { latitude: number; longitude: number };
  vesselSpeed: number;
  onOriginChange: (position: { latitude: number; longitude: number }) => void;
  onDestinationChange: (position: { latitude: number; longitude: number }) => void;
  onVesselSpeedChange: (speed: number) => void;
  onCalculateRoutes?: () => void;
  onClose?: () => void;
  loading?: boolean;
  error?: string | null;
  recommendedProfile?: string;
}

export default function MissionControls({
  origin,
  destination,
  vesselSpeed,
  onOriginChange,
  onDestinationChange,
  onVesselSpeedChange,
  onCalculateRoutes,
  onClose,
  loading = false,
  error = null,
  recommendedProfile,
}: MissionControlsProps) {
  return (
    <aside className="mission-drawer-panel">
      <div className="mission-drawer-header">
        <div>
          <div className="mission-drawer-eyebrow">POLAR OPERATIONS</div>
          <div className="mission-drawer-title">MISSION CONTROL</div>
        </div>

        {onClose && (
          <button type="button" className="mission-drawer-close" onClick={onClose}>
            <X size={17} />
          </button>
        )}
      </div>

      <div className="mission-drawer-body">
        <section className="mission-control-card">
          <div className="mission-card-head">
            <span>MISSION PARAMETERS</span>
            <span className="mission-card-code">NAV-01</span>
          </div>

          <div className="mission-card-body">
            <CoordinateEditor
              label="ORIGIN"
              position={origin}
              onChange={onOriginChange}
            />

            <CoordinateEditor
              label="DESTINATION"
              position={destination}
              onChange={onDestinationChange}
            />

            <div className="mission-field">
              <label>VESSEL</label>
              <div className="mission-static-field">
                <Ship size={14} />
                <span>POLAR RESEARCH VESSEL</span>
              </div>
            </div>

            <div className="mission-field">
              <label>CRUISE SPEED</label>
              <div className="mission-input-field">
                <input
                  type="number"
                  min={1}
                  max={30}
                  step={0.5}
                  value={vesselSpeed}
                  onChange={(event) => onVesselSpeedChange(Number(event.target.value))}
                />
                <span>KNOTS</span>
              </div>
            </div>
          </div>
        </section>

        <section className="mission-control-card">
          <div className="mission-card-head">
            <span>ROUTING PROFILE</span>
            <span className="mission-card-code">NAV-02</span>
          </div>

          <div className="mission-card-body route-profile-list">
            <RouteOption
              name="SAFEST"
              description="Minimize hazard exposure"
              active={recommendedProfile === "safest"}
            />
            <RouteOption
              name="BALANCED"
              description="Risk / distance trade-off"
              active={recommendedProfile === "balanced"}
            />
            <RouteOption
              name="FUEL OPTIMIZED"
              description="Minimize route distance"
              active={recommendedProfile === "fuel_optimized"}
            />

            <button
              type="button"
              className="mission-calculate"
              onClick={onCalculateRoutes}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="mission-pulse" />
                  CALCULATING ROUTES...
                </>
              ) : (
                <>
                  <Crosshair size={14} />
                  CALCULATE ROUTES
                </>
              )}
            </button>

            {error && (
              <div className="mission-error">
                ROUTE ERROR: {error}
              </div>
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}

function CoordinateEditor({
  label,
  position,
  onChange,
}: {
  label: string;
  position: { latitude: number; longitude: number };
  onChange: (position: { latitude: number; longitude: number }) => void;
}) {
  return (
    <div className="mission-field">
      <label>{label}</label>

      <div className="coordinate-grid">
        <div className="mission-input-field">
          <input
            type="number"
            step="0.001"
            value={position.latitude}
            onChange={(event) =>
              onChange({
                ...position,
                latitude: Number(event.target.value),
              })
            }
          />
          <span>LAT</span>
        </div>

        <div className="mission-input-field">
          <input
            type="number"
            step="0.001"
            value={position.longitude}
            onChange={(event) =>
              onChange({
                ...position,
                longitude: Number(event.target.value),
              })
            }
          />
          <span>LON</span>
        </div>
      </div>
    </div>
  );
}

function RouteOption({
  name,
  description,
  active,
}: {
  name: string;
  description: string;
  active: boolean;
}) {
  return (
    <div className={`mission-route-option ${active ? "is-active" : ""}`}>
      <div>
        <strong>{name}</strong>
        <span>{description}</span>
      </div>
      <span className="mission-route-state">{active ? "SELECTED" : "—"}</span>
    </div>
  );
}
