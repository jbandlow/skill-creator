---
name: mapping
description: Work with local OpenStreetMap data for trail analysis, GPX track processing, GPS map matching, and map visualization. Use when the user asks about hiking routes, GPS traces, trail networks, GPX files, or map rendering. All data and services run locally — no external API calls at runtime.
---

# Instruction: mapping

You have access to a local mapping toolkit for trail network analysis, GPX processing, GPS-to-trail map matching, and map visualization. All services run locally using OpenStreetMap data for California.

---

## 1. Infrastructure Overview

### Services

| Service | URL | Purpose |
|---|---|---|
| **Valhalla** | `http://localhost:8002` | Routing engine + map matching (Meili). Matches noisy GPS traces to real OSM trails. |

### Data Locations

| What | Path |
|---|---|
| Valhalla data + docker-compose | `/media/jbandlow/extra/mapping/` |
| PMTiles basemap | `/media/jbandlow/extra/mapping/california.pmtiles` |
| Python package source | `/home/jbandlow/Programming/mapping/` |
| This SKILL | `~/.gemini/antigravity/skills/mapping/` |

### Checking Service Status

```bash
# Is Valhalla running?
curl -s http://localhost:8002/status

# Start Valhalla if not running
cd /media/jbandlow/extra/mapping && docker compose up -d

# View Valhalla logs
cd /media/jbandlow/extra/mapping && docker compose logs -f
```

---

## 2. Python Package Setup

All Python code lives in `/home/jbandlow/Programming/mapping/`. Always run commands from there using `uv run`:

```bash
cd /home/jbandlow/Programming/mapping
uv sync          # First time: install dependencies
uv run pytest    # Run tests
```

---

## 3. Core Recipes

### Recipe 1: Parse a GPX File and Get Stats

```python
from mapping import load_gpx, track_stats

points = load_gpx("/path/to/track.gpx")
stats = track_stats(points)
print(f"Distance: {stats.distance_km:.1f} km")
print(f"Elevation gain: {stats.elevation_gain_m:.0f} m")
print(f"Duration: {stats.duration}")
print(f"Points: {stats.num_points}")
```

### Recipe 2: Map-Match a GPS Trace to Real Trails

This is the core "snap noisy GPS to actual trails" operation. Requires Valhalla running.

```python
from mapping import match_gpx, is_valhalla_ready

assert is_valhalla_ready(), "Start Valhalla: cd /media/jbandlow/extra/mapping && docker compose up -d"

result = match_gpx("/path/to/track.gpx")
print(f"Confidence: {result.confidence:.0%}")
print(f"Matched distance: {result.distance_km:.1f} km")
print(f"Matched points: {len(result.matched_points)}")
```

### Recipe 3: Visualize Raw vs. Matched Trace

```python
from mapping import load_gpx, match_trace, map_track, save_html

points = load_gpx("/path/to/track.gpx")
matched = match_trace(points)

m = map_track(points, matched=matched, title="My Hike")
save_html(m, "hike_map.html")
# Open hike_map.html in a browser to see blue (raw) vs red (matched) traces
```

### Recipe 4: Generate a Static Map Image (PNG)

When you need an image without a browser:

```python
from mapping import load_gpx, static_map

points = load_gpx("/path/to/track.gpx")
path = static_map(points, out_path="hike.png")
print(f"Map saved to: {path}")
```

### Recipe 5: Get Trail Names and Surface Types

```python
from mapping import load_gpx, trace_attributes

points = load_gpx("/path/to/track.gpx")
edges = trace_attributes(points)
for edge in edges:
    if edge.name:
        print(f"{edge.name}: {edge.length_km:.1f} km, surface: {edge.surface}")
```

### Recipe 6: Snap Points to Trail Network Graph (OSMnx)

For graph-based analysis without Valhalla (e.g., finding nearest trail to a point):

```python
from mapping import load_or_build_graph, snap_point, shortest_path

# First call downloads from OSM and caches; subsequent calls load from disk
graph = load_or_build_graph(
    "Muir Woods National Monument, California",
    filepath="data/muir_woods.graphml"
)

# Snap a GPS point to the nearest trail
snapped = snap_point(graph, lat=37.897, lon=-122.581)
print(f"Nearest trail node: {snapped.node_lat}, {snapped.node_lon}")
print(f"Distance from GPS point: {snapped.distance_m:.0f} m")

# Find shortest trail path between two points
path = shortest_path(graph, 37.897, -122.581, 37.894, -122.577)
print(f"Path has {len(path)} nodes")
```

### Recipe 7: Interpolate Position at a Given Time

Useful for "where was I at 10:30 AM?" queries:

```python
from datetime import datetime, timezone
from mapping import load_gpx, interpolate_at

points = load_gpx("/path/to/track.gpx")
target = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
pos = interpolate_at(points, target)
print(f"At {target}: ({pos.lat:.5f}, {pos.lon:.5f})")
```

### Recipe 8: Simplify a Track

Reduce point count for faster processing or cleaner display:

```python
from mapping import load_gpx, simplify

points = load_gpx("/path/to/track.gpx")
simple = simplify(points, tolerance_m=20.0)
print(f"Reduced from {len(points)} to {len(simple)} points")
```

---

## 4. Key Data Types

| Type | Module | Fields |
|---|---|---|
| `TrackPoint` | `gpx_utils` | `lat`, `lon`, `elevation`, `time` |
| `TrackStats` | `gpx_utils` | `distance_km`, `elevation_gain_m`, `elevation_loss_m`, `duration`, `moving_time`, `num_points`, `bounds` |
| `MatchResult` | `match` | `matched_points`, `raw_points`, `confidence`, `distance_km`, `duration_s`, `raw_response` |
| `SnappedPoint` | `trails` | `original`, `nearest_node`, `node_lat`, `node_lon`, `distance_m` |
| `EdgeAttr` | `match` | `name`, `length_km`, `surface`, `way_id`, `begin_shape_index`, `end_shape_index` |

---

## 5. When to Use What

| Task | Tool |
|---|---|
| **Match GPS trace to real trails** | `match_trace()` / `match_gpx()` — Valhalla Meili (best accuracy, handles noise well) |
| **Snap individual points to trails** | `snap_point()` — OSMnx (no server needed, but less sophisticated than Meili) |
| **Get trail names/surfaces** | `trace_attributes()` — Valhalla |
| **Interactive map visualization** | `map_track()` + `save_html()` — Folium/Leaflet |
| **Static map image (PNG)** | `static_map()` — py-staticmaps (no browser needed) |
| **GPX stats and analysis** | `track_stats()`, `interpolate_at()`, `simplify()` — pure Python |
| **Trail routing (A→B on trails)** | `shortest_path()` — OSMnx graph |

---

## 6. Common Gotchas

### Time Zones
GPX timestamps are usually UTC. Camera timestamps may be local time. Always check and convert before comparing.

### Valhalla Trace Density
Meili works best with dense traces (1 point every few seconds). If your GPS logger recorded only every 30-60 seconds, use `shape_match: "map_snap"` (the default) rather than `"edge_walk"`.

### Coordinate Systems
- GPX, Valhalla, and Folium all use **WGS84 (EPSG:4326)** — lat/lon in degrees.
- OSMnx graphs are also WGS84 by default, but call `ox.project_graph()` before distance calculations if you need meter-accurate results.

### OSM Data Gaps
Not all trails are mapped in OpenStreetMap. If map matching confidence is low, the trail may simply not exist in OSM. Check [OpenStreetMap](https://www.openstreetmap.org) to verify trail coverage.

### Valhalla Max Trace Size
Valhalla has a default limit of ~20,000 shape points per request. For very long hikes, split the trace into segments.

---

## 7. Adding New Regions

To add OSM data for a region beyond California:

1. **Valhalla**: Edit `/media/jbandlow/extra/mapping/docker-compose.yml` and add another PBF URL to `tile_urls` (comma-separated). Rebuild with `docker compose down && docker compose up -d`.

2. **PMTiles**: Run the download script with modified bounding box coordinates. Edit `scripts/download_pmtiles.sh` in the mapping repo.

3. **OSMnx graphs**: These are downloaded on demand — just pass a different `place` argument to `load_or_build_graph()`.
