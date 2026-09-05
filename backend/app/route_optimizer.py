from heapq import heappush, heappop
from math import floor
from typing import List, Dict, Tuple

from app.risk_engine import haversine_km
from app.environment_cost import sea_ice_cost


PROFILES = {
    "safest": {
        "distance": 1.0,
        "ice": 5.0,
        "iceberg": 8.0,
    },

    "balanced": {
        "distance": 2.0,
        "ice": 3.0,
        "iceberg": 5.0,
    },

    "fuel_optimized": {
        "distance": 6.0,
        "ice": 1.5,
        "iceberg": 2.0,
    },
}


# ============================================================
# SEA-ICE CONFIGURATION
# ============================================================

# NSIDC-0051 uses a nominal 25 km grid.
#
# A cell-center search radius of ~18 km captures the
# neighborhood represented by a 25 km cell without
# pretending that the concentration applies infinitely far.
SEA_ICE_SEARCH_RADIUS_KM = 18.0


# Spatial index resolution for sea ice.
SEA_ICE_INDEX_RESOLUTION = 0.1

# At Antarctic Peninsula latitudes, searching +/- 4 buckets
# is sufficient to cover the 18 km sea-ice influence radius.
SEA_ICE_INDEX_RADIUS = 4


# ============================================================
# ICEBERG SPATIAL INDEX CONFIGURATION
# ============================================================

# Icebergs are indexed using the same geographic bucket
# philosophy as the sea-ice index.
#
# This is a computational optimization only.
# The actual haversine distance is still calculated before
# an iceberg contributes to the risk score.
ICEBERG_INDEX_RESOLUTION = 0.1

# Search a sufficiently large neighborhood around each
# A* node so relevant nearby icebergs are not discarded
# prematurely.
ICEBERG_INDEX_RADIUS = 4


# ============================================================
# GRID
# ============================================================

def grid_key(
    lat: float,
    lon: float,
) -> Tuple[int, int]:

    return (
        round(lat * 20),
        round(lon * 20),
    )


def key_to_coord(
    key: Tuple[int, int],
) -> Tuple[float, float]:

    return (
        key[0] / 20.0,
        key[1] / 20.0,
    )


def neighbors(
    key: Tuple[int, int],
) -> List[Tuple[int, int]]:

    lat, lon = key

    return [
        (lat + 1, lon),
        (lat - 1, lon),
        (lat, lon + 1),
        (lat, lon - 1),

        (lat + 1, lon + 1),
        (lat + 1, lon - 1),
        (lat - 1, lon + 1),
        (lat - 1, lon - 1),
    ]


# ============================================================
# ICEBERG RISK
# ============================================================

def point_risk(
    lat: float,
    lon: float,
    icebergs: List[Dict[str, float]],
) -> float:

    if not icebergs:
        return 0.0

    risk = 0.0

    for iceberg in icebergs:

        distance = haversine_km(
            lat,
            lon,
            iceberg["latitude"],
            iceberg["longitude"],
        )

        uncertainty = iceberg.get(
            "uncertainty_radius_km",
            0.0,
        )

        effective_distance = max(
            0.1,
            distance - uncertainty,
        )

        risk += 1.0 / effective_distance

    return risk


# ============================================================
# ICEBERG SPATIAL INDEX
# ============================================================

def _iceberg_index_key(
    latitude: float,
    longitude: float,
) -> Tuple[int, int]:

    return (
        floor(
            latitude /
            ICEBERG_INDEX_RESOLUTION
        ),
        floor(
            longitude /
            ICEBERG_INDEX_RESOLUTION
        ),
    )


def build_iceberg_index(
    icebergs: List[Dict[str, float]] | None,
) -> Dict[
    Tuple[int, int],
    List[Dict[str, float]]
]:
    """
    Build a lightweight spatial index over iceberg
    observations.

    Instead of checking every iceberg for every A*
    node, observations are grouped into 0.1-degree
    geographic buckets.

    The index changes computation only.
    Actual haversine distance is still used later.
    """

    index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ] = {}

    if not icebergs:
        return index

    for iceberg in icebergs:

        key = _iceberg_index_key(
            iceberg["latitude"],
            iceberg["longitude"],
        )

        index.setdefault(
            key,
            [],
        ).append(iceberg)

    return index


def _nearby_icebergs(
    lat: float,
    lon: float,
    iceberg_index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ],
) -> List[Dict[str, float]]:
    """
    Return iceberg observations whose geographic
    buckets could intersect the local search area.
    """

    if not iceberg_index:
        return []

    center_lat, center_lon = _iceberg_index_key(
        lat,
        lon,
    )

    candidates: List[
        Dict[str, float]
    ] = []

    for lat_offset in range(
        -ICEBERG_INDEX_RADIUS,
        ICEBERG_INDEX_RADIUS + 1,
    ):

        for lon_offset in range(
            -ICEBERG_INDEX_RADIUS,
            ICEBERG_INDEX_RADIUS + 1,
        ):

            bucket = (
                center_lat + lat_offset,
                center_lon + lon_offset,
            )

            icebergs = iceberg_index.get(
                bucket
            )

            if icebergs:
                candidates.extend(
                    icebergs
                )

    return candidates


def point_risk_indexed(
    lat: float,
    lon: float,
    iceberg_index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ],
) -> float:
    """
    Calculate iceberg routing penalty using the
    spatial index.

    This preserves the original inverse-distance
    risk formulation while avoiding a full scan of
    every iceberg for every A* node.
    """

    candidates = _nearby_icebergs(
        lat,
        lon,
        iceberg_index,
    )

    if not candidates:
        return 0.0

    risk = 0.0

    for iceberg in candidates:

        distance = haversine_km(
            lat,
            lon,
            iceberg["latitude"],
            iceberg["longitude"],
        )

        uncertainty = iceberg.get(
            "uncertainty_radius_km",
            0.0,
        )

        effective_distance = max(
            0.1,
            distance - uncertainty,
        )

        risk += 1.0 / effective_distance

    return risk


# ============================================================
# SEA-ICE SPATIAL INDEX
# ============================================================

def _sea_ice_index_key(
    latitude: float,
    longitude: float,
) -> Tuple[int, int]:

    return (
        floor(
            latitude /
            SEA_ICE_INDEX_RESOLUTION
        ),
        floor(
            longitude /
            SEA_ICE_INDEX_RESOLUTION
        ),
    )


def build_sea_ice_index(
    sea_ice: List[Dict[str, float]] | None,
) -> Dict[
    Tuple[int, int],
    List[Dict[str, float]]
]:
    """
    Build a lightweight spatial index over NSIDC cells.

    Instead of scanning every sea-ice cell for every
    A* node, candidates are grouped into 0.1-degree
    geographic buckets.
    """

    index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ] = {}

    if not sea_ice:
        return index

    for cell in sea_ice:

        key = _sea_ice_index_key(
            cell["latitude"],
            cell["longitude"],
        )

        index.setdefault(
            key,
            [],
        ).append(cell)

    return index


def _nearby_sea_ice_cells(
    lat: float,
    lon: float,
    sea_ice_index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ],
) -> List[Dict[str, float]]:
    """
    Return only sea-ice cells whose geographic
    buckets could possibly intersect the 18 km
    search radius.
    """

    if not sea_ice_index:
        return []

    center_lat, center_lon = _sea_ice_index_key(
        lat,
        lon,
    )

    candidates: List[
        Dict[str, float]
    ] = []

    for lat_offset in range(
        -SEA_ICE_INDEX_RADIUS,
        SEA_ICE_INDEX_RADIUS + 1,
    ):

        for lon_offset in range(
            -SEA_ICE_INDEX_RADIUS,
            SEA_ICE_INDEX_RADIUS + 1,
        ):

            bucket = (
                center_lat + lat_offset,
                center_lon + lon_offset,
            )

            cells = sea_ice_index.get(
                bucket
            )

            if cells:
                candidates.extend(
                    cells
                )

    return candidates


def sea_ice_point_risk(
    lat: float,
    lon: float,
    sea_ice: List[Dict[str, float]] | None,
    profile: str,
) -> float:
    """
    Public-compatible sea-ice risk function.

    This version builds a temporary spatial index and
    is useful when called independently.

    optimize_route() uses a pre-built index so the
    index is not reconstructed for every candidate node.
    """

    if not sea_ice:
        return 0.0

    sea_ice_index = build_sea_ice_index(
        sea_ice
    )

    return sea_ice_point_risk_indexed(
        lat,
        lon,
        sea_ice_index,
        profile,
    )


def sea_ice_point_risk_indexed(
    lat: float,
    lon: float,
    sea_ice_index: Dict[
        Tuple[int, int],
        List[Dict[str, float]]
    ],
    profile: str,
) -> float:
    """
    Calculate the same sea-ice routing penalty as before,
    but only against spatially nearby NSIDC cells.
    """

    if not sea_ice_index:
        return 0.0

    local_risk = 0.0

    nearby_cells = _nearby_sea_ice_cells(
        lat,
        lon,
        sea_ice_index,
    )

    for ice_cell in nearby_cells:

        cell_distance = haversine_km(
            lat,
            lon,
            ice_cell["latitude"],
            ice_cell["longitude"],
        )

        if cell_distance <= SEA_ICE_SEARCH_RADIUS_KM:

            concentration = ice_cell.get(
                "concentration",
                0.0,
            )

            # Give closer cells more influence while
            # keeping the contribution bounded.
            proximity = max(
                0.0,
                1.0
                - (
                    cell_distance /
                    SEA_ICE_SEARCH_RADIUS_KM
                ),
            )

            local_risk = max(
                local_risk,
                sea_ice_cost(
                    concentration,
                    profile,
                )
                * proximity,
            )

    return local_risk


# ============================================================
# PATH RECONSTRUCTION
# ============================================================

def reconstruct_path(
    came_from: Dict,
    current: Tuple[int, int],
) -> List[Tuple[int, int]]:

    path = [current]

    while current in came_from:

        current = came_from[current]

        path.append(current)

    path.reverse()

    return path


# ============================================================
# A* ROUTE OPTIMIZATION
# ============================================================

def optimize_route(
    start_lat: float,
    start_lon: float,
    destination_lat: float,
    destination_lon: float,
    icebergs: List[Dict[str, float]],
    profile: str = "balanced",
    sea_ice: List[Dict[str, float]] | None = None,
    grid_resolution: float = 0.05,
    max_iterations: int = 50000,
) -> dict:

    if profile not in PROFILES:

        raise ValueError(
            f"Unknown profile: {profile}. "
            f"Choose from {list(PROFILES.keys())}"
        )

    weights = PROFILES[profile]

    start = grid_key(
        start_lat,
        start_lon,
    )

    goal = grid_key(
        destination_lat,
        destination_lon,
    )

    # --------------------------------------------------------
    # Build spatial indexes ONCE.
    # --------------------------------------------------------

    sea_ice_index = build_sea_ice_index(
        sea_ice
    )

    iceberg_index = build_iceberg_index(
        icebergs
    )

    # --------------------------------------------------------
    # Cache risk calculations for route grid nodes.
    #
    # A* can revisit the same geographic node multiple times.
    # There is no reason to recompute the same risk.
    # --------------------------------------------------------

    iceberg_risk_cache: Dict[
        Tuple[int, int],
        float
    ] = {}

    sea_ice_risk_cache: Dict[
        Tuple[int, int],
        float
    ] = {}

    def cached_iceberg_risk(
        key: Tuple[int, int],
    ) -> float:

        if key not in iceberg_risk_cache:

            lat, lon = key_to_coord(
                key
            )

            iceberg_risk_cache[key] = (
                point_risk_indexed(
                    lat,
                    lon,
                    iceberg_index,
                )
            )

        return iceberg_risk_cache[key]

    def cached_sea_ice_risk(
        key: Tuple[int, int],
    ) -> float:

        if key not in sea_ice_risk_cache:

            lat, lon = key_to_coord(
                key
            )

            sea_ice_risk_cache[key] = (
                sea_ice_point_risk_indexed(
                    lat,
                    lon,
                    sea_ice_index,
                    profile,
                )
            )

        return sea_ice_risk_cache[key]

    # --------------------------------------------------------
    # A* initialization
    # --------------------------------------------------------

    open_set = []

    heappush(
        open_set,
        (
            0.0,
            start,
        ),
    )

    came_from = {}

    g_score = {
        start: 0.0
    }

    iterations = 0

    # --------------------------------------------------------
    # A* search
    # --------------------------------------------------------

    while (
        open_set
        and iterations < max_iterations
    ):

        iterations += 1

        _, current = heappop(
            open_set
        )

        if current == goal:

            path = reconstruct_path(
                came_from,
                current,
            )

            coordinates = [
                {
                    "latitude": key_to_coord(
                        point
                    )[0],

                    "longitude": key_to_coord(
                        point
                    )[1],
                }

                for point in path
            ]

            # ------------------------------------------------
            # Final route metrics
            # ------------------------------------------------

            total_distance = 0.0
            total_risk = 0.0

            for i in range(
                1,
                len(coordinates),
            ):

                segment_distance = haversine_km(
                    coordinates[i - 1][
                        "latitude"
                    ],
                    coordinates[i - 1][
                        "longitude"
                    ],
                    coordinates[i][
                        "latitude"
                    ],
                    coordinates[i][
                        "longitude"
                    ],
                )

                total_distance += (
                    segment_distance
                )

                total_risk += (
                    point_risk_indexed(
                        coordinates[i][
                            "latitude"
                        ],
                        coordinates[i][
                            "longitude"
                        ],
                        iceberg_index,
                    )
                )

            return {
                "status": "success",

                "profile": profile,

                "distance_km": round(
                    total_distance,
                    3,
                ),

                "risk_score": round(
                    total_risk,
                    3,
                ),

                "points": coordinates,

                "iterations": iterations,
            }

        current_lat, current_lon = (
            key_to_coord(current)
        )

        # ----------------------------------------------------
        # Explore neighboring grid cells
        # ----------------------------------------------------

        for neighbor in neighbors(
            current
        ):

            neighbor_lat, neighbor_lon = (
                key_to_coord(neighbor)
            )

            # -----------------------------------------------
            # Distance cost
            # -----------------------------------------------

            segment_distance = haversine_km(
                current_lat,
                current_lon,
                neighbor_lat,
                neighbor_lon,
            )

            # -----------------------------------------------
            # Cached + spatially indexed iceberg risk
            # -----------------------------------------------

            iceberg_risk = (
                cached_iceberg_risk(
                    neighbor
                )
            )

            # -----------------------------------------------
            # Cached + spatially indexed sea-ice risk
            # -----------------------------------------------

            ice_risk = (
                cached_sea_ice_risk(
                    neighbor
                )
            )

            # -----------------------------------------------
            # Combined movement cost
            # -----------------------------------------------

            movement_cost = (
                weights["distance"]
                * segment_distance

                + weights["iceberg"]
                * iceberg_risk

                + weights["ice"]
                * ice_risk
            )

            tentative_g = (
                g_score[current]
                + movement_cost
            )

            if (
                neighbor not in g_score
                or tentative_g
                < g_score[neighbor]
            ):

                came_from[neighbor] = (
                    current
                )

                g_score[neighbor] = (
                    tentative_g
                )

                heuristic = haversine_km(
                    neighbor_lat,
                    neighbor_lon,
                    destination_lat,
                    destination_lon,
                )

                f_score = (
                    tentative_g
                    + weights["distance"]
                    * heuristic
                )

                heappush(
                    open_set,
                    (
                        f_score,
                        neighbor,
                    ),
                )

    # --------------------------------------------------------
    # No route found
    # --------------------------------------------------------

    return {
        "status": "failed",

        "profile": profile,

        "reason":
            "No route found within iteration limit.",
    }