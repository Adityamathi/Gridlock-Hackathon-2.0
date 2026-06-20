"""
Real-time ingestion framework with simulation mode for demo.

Usage in app:
  from realtime_ingest import RealtimeIngester, SimulatedEventSource
  ingester = RealtimeIngester()
  ingester.register_source("simulation", SimulatedEventSource())
  ingester.start_background(poll_interval=30)
  ingester.get_buffered_events()  # returns new events since last check
"""


import json
import random
import time
import logging
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone, timedelta
logger = logging.getLogger(__name__)

# Bangalore-area bounding box
BLR_LAT_RANGE = (12.87, 13.10)
BLR_LON_RANGE = (77.50, 77.72)

CAUSES = [
    "accident", "congestion", "vehiclebreakdown", "public_event",
    "procession", "construction", "waterlogging", "potholes",
]

CORRIDORS = [
    "Mysore Road", "Bellary Road 1", "Bellary Road 2", "Tumkur Road",
    "Old Airport Road", "Hosur Road", "ORR East 1", "ORR West 1",
    "ORR North 1", "Bannerghata Road", "CBD 1",
]

CORRIDOR_COORDS = {
    "Mysore Road": (12.9413, 77.5200),
    "Bellary Road 1": (13.0320, 77.6050),
    "Bellary Road 2": (13.0600, 77.6100),
    "Tumkur Road": (13.0100, 77.5400),
    "Old Airport Road": (12.9600, 77.6500),
    "Hosur Road": (12.9000, 77.6300),
    "ORR East 1": (12.9600, 77.6800),
    "ORR West 1": (12.9300, 77.5700),
    "ORR North 1": (13.0400, 77.6300),
    "Bannerghata Road": (12.9100, 77.5900),
    "CBD 1": (12.9750, 77.6050),
}


class IngestedEvent:
    """Normalized event from any real-time source."""

    def __init__(self, source, lat, lon, cause, event_type="unplanned",
                 corridor=None, timestamp=None, confidence=0.5, metadata=None):
        self.source = source
        self.latitude = lat
        self.longitude = lon
        self.event_cause = cause
        self.event_type = event_type
        self.corridor = corridor or "Non-corridor"
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.confidence = confidence
        self.metadata = metadata or {}
        ts_floor = self.timestamp.strftime("%Y-%m-%d %H:%M")
        self._dedup_key = f"{source}|{lat:.4f}|{lon:.4f}|{cause}|{ts_floor}"

    def to_sample(self):
        return {
            "event_type": self.event_type,
            "event_cause": self.event_cause,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "corridor": self.corridor,
            "zone": "Unknown",
            "junction": "Unknown",
            "hour": self.timestamp.hour,
            "day_of_week": self.timestamp.weekday(),
            "month": self.timestamp.month,
            "is_weekend": 1 if self.timestamp.weekday() >= 5 else 0,
            "expected_attendance": random.randint(100, 15000) if self.event_cause in ("public_event", "procession") else 0,
        }

    def to_dict(self):
        return {
            "source": self.source,
            "time": self.timestamp.strftime("%H:%M:%S"),
            "cause": self.event_cause,
            "corridor": self.corridor,
            "lat": round(self.latitude, 4),
            "lon": round(self.longitude, 4),
            "confidence": self.confidence,
        }


class SimulatedEventSource:
    """Generates realistic events based on historical patterns for demo/monitoring."""

    def __init__(self, poll_interval=30):
        self.poll_interval = poll_interval
        self._last_poll = datetime.now(timezone.utc)
        self._event_count = 0

    def poll(self):
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_poll).total_seconds()
        if elapsed < self.poll_interval:
            return []
        self._last_poll = now
        self._event_count += 1

        hour = now.hour
        is_peak = hour in (8, 9, 17, 18, 19)
        is_night = hour < 6 or hour > 22

        # Base event probability — higher during peak hours
        if is_peak:
            prob = 0.6
        elif is_night:
            prob = 0.1
        else:
            prob = 0.3

        if random.random() > prob:
            return []

        # Generate 1-2 events
        count = random.choices([1, 2], weights=[0.7, 0.3])[0]
        events = []
        for _ in range(count):
            cause = random.choices(CAUSES, weights=[25, 22, 15, 8, 5, 12, 8, 5])[0]
            corridor = random.choice(CORRIDORS)
            clat, clon = CORRIDOR_COORDS[corridor]
            lat = clat + random.uniform(-0.02, 0.02)
            lon = clon + random.uniform(-0.02, 0.02)
            event_type = "unplanned" if cause not in ("public_event", "procession") else "planned"
            confidence = random.uniform(0.5, 0.95)
            events.append(IngestedEvent(
                source="simulation",
                lat=lat, lon=lon, cause=cause,
                event_type=event_type,
                corridor=corridor,
                timestamp=now,
                confidence=confidence,
                metadata={"sim_id": self._event_count},
            ))
        return events

    @property
    def name(self):
        return "Simulation"


class AStramEventSource:
    """Polls the ASTraM Bangalore Traffic Police API for real-time events.

    Requires api_key and optional api_url set via Streamlit secrets.
    Falls back to "not configured" state when key is missing.
    """

    def __init__(self, api_key="", api_url="", poll_interval=60):
        self.api_key = api_key
        self.api_url = api_url or "https://api.astram.btp.gov.in/v1/events"
        self.poll_interval = poll_interval
        self._last_poll = datetime.now(timezone.utc)
        self._error = None
        self._configured = bool(api_key)

    def poll(self):
        now = datetime.now(timezone.utc)
        if (now - self._last_poll).total_seconds() < self.poll_interval:
            return []
        self._last_poll = now

        if not self._configured:
            return []

        try:
            req = Request(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                method="GET",
            )
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            self._error = None
            return self._parse_response(data)
        except HTTPError as e:
            self._error = f"HTTP {e.code}: {e.reason}"
        except (URLError, OSError) as e:
            self._error = f"Connection failed: {e.reason if hasattr(e, 'reason') else e}"
        except json.JSONDecodeError:
            self._error = "Invalid JSON response"
        return []

    def _parse_response(self, data):
        """Convert ASTraM API response into IngestedEvent list.

        Expected format (adjust to actual API):
          {"events": [{"id": "...", "type": "accident", "lat": ..., "lon": ...,
                       "timestamp": "ISO8601", "confidence": 0.9}, ...]}
        """
        items = data if isinstance(data, list) else data.get("events", [])
        events = []
        for item in items:
            cause = str(item.get("type", item.get("cause", "congestion"))).lower().replace(" ", "")
            lat = float(item.get("latitude", item.get("lat", 0)))
            lon = float(item.get("longitude", item.get("lon", 0)))
            ts_str = item.get("timestamp", item.get("time", ""))
            ts = None
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    ts = None
            events.append(IngestedEvent(
                source="astram",
                lat=lat, lon=lon, cause=cause,
                timestamp=ts or datetime.now(timezone.utc),
                confidence=float(item.get("confidence", 0.7)),
                metadata={"id": item.get("id"), "raw": item},
            ))
        return events

    @property
    def name(self):
        return "ASTraM API"


class TrafficEventSource:
    """Polls a generic Traffic Data API (TomTom / HERE / Google) for incidents.

    Requires api_key and optional api_url set via Streamlit secrets.
    """

    def __init__(self, api_key="", api_url="", poll_interval=60, bbox=None):
        self.api_key = api_key
        self.api_url = api_url
        self.poll_interval = poll_interval
        self._last_poll = datetime.now(timezone.utc)
        self._error = None
        self._configured = bool(api_key)
        self.bbox = bbox or "12.87,77.50,13.10,77.72"  # Bangalore

    def _do_poll(self):
        """Actual HTTP request — separated for retry logic."""
        if not self.api_url:
            bbox_parts = self.bbox.split(",")
            if len(bbox_parts) == 4:
                lat1, lon1, lat2, lon2 = bbox_parts
                # Bing expects minLat,minLon,maxLat,maxLon (our format)
                bbox_str = f"{min(lat1,lat2)},{min(lon1,lon2)},{max(lat1,lat2)},{max(lon1,lon2)}"
            else:
                bbox_str = self.bbox
            # Bing Maps Traffic Incidents API (free tier)
            url = (
                f"https://dev.virtualearth.net/REST/v1/Traffic/Incidents/"
                f"{bbox_str}"
                f"?key={self.api_key}&o=json&t=1,2,3,4,5,6,7,8,9,10,11,14"
            )
        else:
            url = self.api_url
        req = Request(url, headers={"Accept": "application/json"}, method="GET")
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        # Detect API-level errors (TomTom returns 200 with error body)
        if isinstance(data, dict):
            err = data.get("error") or data.get("errorCode") or data.get("error_description") or data.get("error_msg") or data.get("message")
            if err:
                self._error = str(err)
                return {"incidents": []}
        return self._parse_response(data)

    def poll(self):
        now = datetime.now(timezone.utc)
        if (now - self._last_poll).total_seconds() < self.poll_interval:
            return []
        self._last_poll = now

        if not self._configured:
            return []

        # Retry once on transient DNS/network errors
        for attempt in range(2):
            try:
                result = self._do_poll()
                self._error = None
                return result
            except HTTPError as e:
                body = e.read().decode(errors="ignore")[:300] if hasattr(e, 'read') else ""
                self._error = f"HTTP {e.code}: {e.reason}{' — ' + body if body else ''}"
                break  # don't retry on auth/4xx errors
            except (URLError, OSError) as e:
                err_msg = f"Connection failed: {e.reason if hasattr(e, 'reason') else e}"
                if attempt == 0 and "getaddrinfo" in err_msg:
                    time.sleep(1)
                    continue  # retry once on DNS failure
                self._error = err_msg
                break
            except json.JSONDecodeError:
                self._error = "Invalid JSON response"
                break
        return []

    def _parse_v5_item(self, item):
        """Parse a single TomTom v5 incident item into an IngestedEvent or None."""
        props = item.get("properties", {})
        icon_cat = props.get("iconCategory", 0)

        ic_map = {
            1: "accident", 6: "congestion", 7: "lane_closed", 8: "road_closed",
            9: "construction", 11: "flooding", 14: "vehiclebreakdown",
        }
        cause = ic_map.get(icon_cat, "congestion")

        events_list = props.get("events", [])
        if events_list:
            desc = events_list[0].get("description", "").lower()
            desc_map = {
                "accident": "accident", "collision": "accident", "crash": "accident",
                "broken": "vehiclebreakdown", "breakdown": "vehiclebreakdown",
                "flood": "flooding", "water": "flooding",
                "construction": "construction", "roadwork": "construction",
                "closed": "road_closed", "closure": "road_closed",
                "jam": "congestion", "congestion": "congestion", "slow": "congestion",
            }
            for key, val in desc_map.items():
                if key in desc:
                    cause = val
                    break

        geom = item.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        if geom.get("type") == "Point" and len(coords) >= 2:
            lon, lat = coords[0], coords[1]
        elif isinstance(coords, list) and coords and isinstance(coords[0], list):
            mid = coords[len(coords) // 2]
            lon, lat = mid[0], mid[1]
        else:
            lon, lat = 0, 0

        conf = min(props.get("magnitudeOfDelay", 2) / 4.0, 0.95)
        if conf < 0.1:
            conf = 0.5

        ts_str = props.get("startTime", "")
        ts = None
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                ts = None

        return IngestedEvent(
            source="traffic_api",
            lat=lat, lon=lon, cause=cause,
            timestamp=ts or datetime.now(timezone.utc),
            confidence=conf,
            metadata={
                "id": props.get("id"),
                "from": props.get("from"),
                "to": props.get("to"),
                "icon_category": icon_cat,
            },
        )

    def _parse_bing_item(self, item):
        """Parse a single Bing Maps Traffic Incident into an IngestedEvent or None."""
        severity = item.get("severity", 2)
        bing_type = item.get("type", 5)
        road_closed = item.get("roadClosed", False)
        desc = (item.get("description", "") or "").lower()

        # Bing type → cause
        type_map = {
            1: "accident", 2: "congestion", 3: "vehiclebreakdown",
            7: "public_event", 9: "construction",
            8: "accident", 10: "congestion", 11: "weather",
        }
        cause = type_map.get(bing_type, "congestion")
        if road_closed:
            cause = "road_closed"
        # Override with description match if clearer
        desc_map = {
            "accident": "accident", "collision": "accident",
            "broken": "vehiclebreakdown", "breakdown": "vehiclebreakdown",
            "flood": "flooding", "construction": "construction",
            "closed": "road_closed", "closure": "road_closed",
        }
        for key, val in desc_map.items():
            if key in desc:
                cause = val
                break

        point = item.get("point", {})
        coords = point.get("coordinates", [0, 0])
        lat = float(coords[0]) if coords else 0
        lon = float(coords[1]) if len(coords) > 1 else 0

        conf = min(severity / 4.0, 0.95)
        if conf < 0.1:
            conf = 0.5

        return IngestedEvent(
            source="traffic_api",
            lat=lat, lon=lon, cause=cause,
            timestamp=datetime.now(timezone.utc),
            confidence=conf,
            metadata={
                "id": item.get("incidentId"),
                "description": item.get("description"),
                "road_closed": road_closed,
            },
        )

    def _parse_response(self, data):
        """Detect API provider and parse accordingly."""
        if not isinstance(data, dict):
            return []

        # Bing format: {"resourceSets": [{"resources": [...]}]}
        if "resourceSets" in data:
            events = []
            for rs in data["resourceSets"]:
                for item in rs.get("resources", []):
                    try:
                        ev = self._parse_bing_item(item)
                        if ev:
                            events.append(ev)
                    except Exception:
                        continue
            return events

        # TomTom v5 format: {"incidents": [...]}
        items = data.get("incidents", data.get("tm", {}).get("poi", []))
        if not items and isinstance(items, list):
            return []
        events = []
        for item in items:
            try:
                ev = self._parse_v5_item(item)
                if ev:
                    events.append(ev)
            except Exception:
                continue
        return events

    @property
    def name(self):
        return "Traffic API"


class RealtimeIngester:
    """Orchestrates data sources, deduplicates, and buffers events."""

    def __init__(self):
        self.sources = {}
        self._seen_keys = set()
        self._buffer = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def register_source(self, name, source):
        self.sources[name] = source

    def poll_all(self):
        new_events = []
        for name, source in self.sources.items():
            try:
                events = source.poll() if hasattr(source, 'poll') else []
                for ev in events:
                    if ev._dedup_key not in self._seen_keys:
                        self._seen_keys.add(ev._dedup_key)
                        new_events.append(ev)
            except Exception as e:
                logger.error(f"Error polling {name}: {e}")
        return new_events

    def start_background(self, poll_interval=30):
        def _loop():
            while self._running:
                events = self.poll_all()
                with self._lock:
                    self._buffer.extend(events)
                time.sleep(poll_interval)
        self._running = True
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_buffered_events(self):
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def get_source_status(self):
        return {name: {
            "type": src.__class__.__name__,
            "poll_interval_s": getattr(src, "poll_interval", None),
            "configured": getattr(src, "_configured", False),
            "error": getattr(src, "_error", None),
        } for name, src in self.sources.items()}
