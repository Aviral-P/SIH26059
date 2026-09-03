-- ============================================================
-- Antarctic Navigation Intelligence
-- PostGIS Database Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 1. ICEBERG OBSERVATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS iceberg_observations (
    id BIGSERIAL PRIMARY KEY,

    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(150),

    observed_at TIMESTAMPTZ,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    area_km2 DOUBLE PRECISION,
    mass_gt DOUBLE PRECISION,

    long_axis_km DOUBLE PRECISION,
    short_axis_km DOUBLE PRECISION,
    perimeter_km DOUBLE PRECISION,

    detection_method VARCHAR(100),

    geometry GEOMETRY(Point, 4326),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_latitude
        CHECK (latitude BETWEEN -90 AND 90),

    CONSTRAINT valid_longitude
        CHECK (longitude BETWEEN -180 AND 180)
);

CREATE INDEX IF NOT EXISTS idx_iceberg_observations_geom
ON iceberg_observations
USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_iceberg_observations_time
ON iceberg_observations (observed_at);

CREATE INDEX IF NOT EXISTS idx_iceberg_observations_source
ON iceberg_observations (source);

-- ============================================================
-- 2. ICEBERG TRAJECTORIES
-- ============================================================

CREATE TABLE IF NOT EXISTS iceberg_trajectories (
    id BIGSERIAL PRIMARY KEY,

    source VARCHAR(50) NOT NULL,
    iceberg_id VARCHAR(150) NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    displacement_km DOUBLE PRECISION,
    velocity_kmh DOUBLE PRECISION,
    velocity_angle_deg DOUBLE PRECISION,

    geometry GEOMETRY(Point, 4326),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trajectory_geom
ON iceberg_trajectories
USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_trajectory_iceberg_id
ON iceberg_trajectories (iceberg_id);

CREATE INDEX IF NOT EXISTS idx_trajectory_time
ON iceberg_trajectories (observed_at);

-- ============================================================
-- 3. ICEBERG TRACK LINES
-- ============================================================

CREATE TABLE IF NOT EXISTS iceberg_tracks (
    id BIGSERIAL PRIMARY KEY,

    source VARCHAR(50) NOT NULL,
    iceberg_id VARCHAR(150) NOT NULL,

    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,

    point_count INTEGER,

    track_geometry GEOMETRY(LineString, 4326),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_iceberg_tracks_geom
ON iceberg_tracks
USING GIST (track_geometry);

CREATE INDEX IF NOT EXISTS idx_iceberg_tracks_id
ON iceberg_tracks (iceberg_id);

-- ============================================================
-- 4. ENVIRONMENTAL GRID METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS environmental_datasets (
    id BIGSERIAL PRIMARY KEY,

    dataset_name VARCHAR(100) NOT NULL,
    variable_name VARCHAR(100) NOT NULL,

    source VARCHAR(100),

    valid_time TIMESTAMPTZ,

    file_path TEXT,

    spatial_resolution DOUBLE PRECISION,

    unit VARCHAR(50),

    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_environmental_time
ON environmental_datasets (valid_time);

-- ============================================================
-- 5. VESSELS
-- ============================================================

CREATE TABLE IF NOT EXISTS vessels (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    vessel_type VARCHAR(100),

    max_speed_knots DOUBLE PRECISION,
    cruise_speed_knots DOUBLE PRECISION,

    length_m DOUBLE PRECISION,
    beam_m DOUBLE PRECISION,
    draft_m DOUBLE PRECISION,

    fuel_rate_lph DOUBLE PRECISION,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 6. MISSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS missions (
    id BIGSERIAL PRIMARY KEY,

    mission_name VARCHAR(200) NOT NULL,

    vessel_id BIGINT REFERENCES vessels(id),

    start_lat DOUBLE PRECISION,
    start_lon DOUBLE PRECISION,

    destination_lat DOUBLE PRECISION,
    destination_lon DOUBLE PRECISION,

    departure_time TIMESTAMPTZ,

    mission_profile VARCHAR(50),

    status VARCHAR(50) DEFAULT 'planned',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. ROUTES
-- ============================================================

CREATE TABLE IF NOT EXISTS routes (
    id BIGSERIAL PRIMARY KEY,

    mission_id BIGINT REFERENCES missions(id),

    route_type VARCHAR(50),

    distance_km DOUBLE PRECISION,

    estimated_hours DOUBLE PRECISION,

    fuel_estimate_l DOUBLE PRECISION,

    risk_score DOUBLE PRECISION,

    ice_exposure_score DOUBLE PRECISION,

    iceberg_risk_score DOUBLE PRECISION,

    route_geometry GEOMETRY(LineString, 4326),

    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routes_geom
ON routes
USING GIST (route_geometry);

CREATE INDEX IF NOT EXISTS idx_routes_mission
ON routes (mission_id);

-- ============================================================
-- 8. RISK ZONES
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_zones (
    id BIGSERIAL PRIMARY KEY,

    risk_type VARCHAR(100) NOT NULL,

    risk_score DOUBLE PRECISION NOT NULL,

    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,

    probability DOUBLE PRECISION,

    geometry GEOMETRY(Polygon, 4326),

    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_zones_geom
ON risk_zones
USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_risk_zones_time
ON risk_zones (valid_from, valid_to);

-- ============================================================
-- 9. DRIFT FORECASTS
-- ============================================================

CREATE TABLE IF NOT EXISTS iceberg_drift_forecasts (
    id BIGSERIAL PRIMARY KEY,

    iceberg_id VARCHAR(150) NOT NULL,

    forecast_time TIMESTAMPTZ NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    predicted_speed_kmh DOUBLE PRECISION,
    predicted_heading_deg DOUBLE PRECISION,

    uncertainty_radius_km DOUBLE PRECISION,

    model_name VARCHAR(100),

    geometry GEOMETRY(Point, 4326),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drift_forecast_geom
ON iceberg_drift_forecasts
USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_drift_forecast_iceberg
ON iceberg_drift_forecasts (iceberg_id);

CREATE INDEX IF NOT EXISTS idx_drift_forecast_time
ON iceberg_drift_forecasts (forecast_time);

-- ============================================================
-- 10. SYSTEM METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS dataset_registry (
    id BIGSERIAL PRIMARY KEY,

    dataset_name VARCHAR(150) UNIQUE NOT NULL,

    source VARCHAR(150),

    version VARCHAR(100),

    description TEXT,

    temporal_start TIMESTAMPTZ,
    temporal_end TIMESTAMPTZ,

    spatial_crs VARCHAR(50),

    local_path TEXT,

    metadata JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);