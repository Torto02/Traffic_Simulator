from .vehicle_generator import VehicleGenerator
from .geometry.quadratic_curve import QuadraticCurve
from .geometry.cubic_curve import CubicCurve
from .geometry.segment import Segment
from .vehicle import Vehicle


class Simulation:
    def __init__(self):
        self.segments = []
        self.segment_by_id = {}
        self.vehicles = {}
        self.vehicle_generator = []
        self.environment = []  # static environment objects (trees, lamps, RSUs, etc.)
        self.events = []  # scheduled events (accidents, works, animals)
        self.active_event_ids = set()
        self.segment_event_factors = {}
        self.segment_events_by_idx = {}
        self.event_lookahead = 50  # meters to look ahead for event-based slowdown
        self.junctions = {}  # id -> junction dict
        self.segment_junctions = {}  # seg_idx -> list of approach dicts

        # Routing graph (directed) built over segment endpoints
        self.graph = {}
        self._graph_dirty = True
        self.graph_tol = 5e-2  # tolerance for snapping endpoints when building connectivity

        self.t = 0.0
        self.frame_count = 0
        self.dt = 1/60  


    def add_vehicle(self, veh):
        # Resolve/compute path identifiers to indices and register vehicle.
        self.prepare_vehicle_path(veh)
        self.vehicles[veh.id] = veh
        if len(veh.path) > 0:
            self.segments[veh.path[0]].add_vehicle(veh)

    def add_segment(self, seg):
        # Keep lookup by segment id (when provided) for path resolution.
        if seg.id is not None:
            if seg.id in self.segment_by_id:
                raise ValueError(f"Segment id '{seg.id}' already exists")
            self.segment_by_id[seg.id] = len(self.segments)
        self.segments.append(seg)
        self._graph_dirty = True

    def add_vehicle_generator(self, gen):
        self.vehicle_generator.append(gen)

    def add_environment_object(self, obj):
        # obj is expected to be a dict-like structure with at least a type and position
        self.environment.append(obj)

    def add_event(self, event):
        """Register a timed event; assigns an id if missing."""
        if "id" not in event or event.get("id") is None:
            event["id"] = f"event_{len(self.events)}"
        self.events.append(event)

    def add_junction(self, junction):
        """Register a junction with approaches and optional traffic lights."""
        jid = junction.get("id", f"junction_{len(self.junctions)}")
        junction["id"] = jid
        self.junctions[jid] = junction

    def create_vehicle(self, **kwargs):
        veh = Vehicle(kwargs)
        self.add_vehicle(veh)

    def create_segment(self, *points, **metadata):
        seg = Segment(points, **metadata)
        self.add_segment(seg)

    def create_quadratic_bezier_curve(self, start, control, end, **metadata):
        cur = QuadraticCurve(start, control, end, **metadata)
        self.add_segment(cur)

    def create_cubic_bezier_curve(self, start, control_1, control_2, end, **metadata):
        cur = CubicCurve(start, control_1, control_2, end, **metadata)
        self.add_segment(cur)

    def create_vehicle_generator(self, **kwargs):
        gen = VehicleGenerator(kwargs)
        self.add_vehicle_generator(gen)

    def _point_key(self, pt, tol):
        """Quantize a point to an integer grid to detect connectivity with tolerance."""
        return (round(pt[0] / tol), round(pt[1] / tol))

    def rebuild_graph(self, tol=None):
        """Build a directed graph where edges follow segment direction (start -> end)."""
        tol = tol or self.graph_tol
        start_map = {}
        end_map = {}
        for seg_id, idx in self.segment_by_id.items():
            seg = self.segments[idx]
            if not seg.points:
                continue
            start_key = self._point_key(seg.points[0], tol)
            end_key = self._point_key(seg.points[-1], tol)
            start_map.setdefault(start_key, []).append(seg_id)
            end_map.setdefault(end_key, []).append(seg_id)

        graph = {sid: [] for sid in self.segment_by_id}
        for end_key, from_list in end_map.items():
            to_list = start_map.get(end_key, [])
            for u in from_list:
                for v in to_list:
                    if u == v:
                        continue
                    cost = self.segments[self.segment_by_id[v]].get_length()
                    graph[u].append((v, cost))

        self.graph = graph
        self._graph_dirty = False
        return start_map, end_map

    def _dijkstra_path(self, start_seg_id, end_seg_id):
        import heapq

        dist = {start_seg_id: 0.0}
        prev = {}
        heap = [(0.0, start_seg_id)]

        while heap:
            cur_dist, u = heapq.heappop(heap)
            if u == end_seg_id:
                break
            if cur_dist != dist.get(u, float("inf")):
                continue
            for v, cost in self.graph.get(u, []):
                alt = cur_dist + cost
                if alt < dist.get(v, float("inf")):
                    dist[v] = alt
                    prev[v] = u
                    heapq.heappush(heap, (alt, v))

        if end_seg_id not in prev and end_seg_id != start_seg_id:
            return None, None

        path = [end_seg_id]
        while path[-1] != start_seg_id:
            path.append(prev[path[-1]])
        path.reverse()
        return path, dist.get(end_seg_id, 0.0)

    def shortest_path(self, start_seg_id, end_seg_id):
        """Return a list of segment ids forming the shortest directed path (by length).

        If no path is found with the current tolerance, retry once with a looser
        tolerance (5x) before failing to help with near-miss endpoints.
        """
        if start_seg_id not in self.segment_by_id:
            raise ValueError(f"Unknown start segment id '{start_seg_id}'")
        if end_seg_id not in self.segment_by_id:
            raise ValueError(f"Unknown end segment id '{end_seg_id}'")

        if self._graph_dirty:
            self.rebuild_graph()

        if start_seg_id == end_seg_id:
            return [start_seg_id]

        path, _ = self._dijkstra_path(start_seg_id, end_seg_id)
        if path is not None:
            return path

        # Retry with looser tolerance
        loose_tol = self.graph_tol * 5
        self.rebuild_graph(loose_tol)
        path, _ = self._dijkstra_path(start_seg_id, end_seg_id)
        if path is not None:
            print(f"[routing] rebuilt graph with tol={loose_tol} to connect {start_seg_id}->{end_seg_id}")
            return path

        # Diagnostics: show endpoint distances to help debugging
        start_seg = self.segments[self.segment_by_id[start_seg_id]]
        end_seg = self.segments[self.segment_by_id[end_seg_id]]
        start_endpt = start_seg.points[-1]
        end_startpt = end_seg.points[0]
        msg = (
            f"No path found from '{start_seg_id}' to '{end_seg_id}'. "
            f"End of start {start_endpt}, start of end {end_startpt}, tol tried {self.graph_tol} and {loose_tol}."
        )
        raise ValueError(msg)

    def prepare_vehicle_path(self, veh):
        """Ensure vehicle.path is resolved; auto-route if start/end are provided."""
        if (not veh.path or len(veh.path) == 0) and veh.start_segment and veh.end_segment:
            veh.path = self.shortest_path(veh.start_segment, veh.end_segment)
        if not veh.path:
            raise ValueError("Vehicle has no path and no start/end routing information")
        veh.path = self.resolve_path(veh.path)

        # Log chosen path with length for diagnostics (helpful to compare alternatives)
        try:
            total_len = sum(self.segments[idx].get_length() for idx in veh.path)
            print(
                f"[routing] class={getattr(veh, 'vehicle_class', None)} "
                f"start={veh.start_segment} end={veh.end_segment} "
                f"path_ids={[self.segments[i].id for i in veh.path]} "
                f"length={total_len:.2f}"
            )
        except Exception:
            # Do not fail simulation because of logging
            pass

        return veh.path

    def resolve_path(self, path_spec):
        """Return list of segment indices from a path specification.

        Accepts integers (existing behavior) or segment ids (strings).
        Raises ValueError if an id is unknown.
        """
        resolved = []
        for item in path_spec:
            if isinstance(item, str):
                if item not in self.segment_by_id:
                    raise ValueError(f"Unknown segment id '{item}' in path")
                resolved.append(self.segment_by_id[item])
            else:
                resolved.append(item)
        return resolved

    def run(self, steps):
        for _ in range(steps):
            self.update()

    def update(self):
        # Update junction timing and mappings
        self._update_junctions()
        # Update events and compute per-segment speed factors
        self._update_events()

        # Update vehicles
        for seg_idx, segment in enumerate(self.segments):
            if len(segment.vehicles) != 0:
                lead = self.vehicles[segment.vehicles[0]]
                factor = self._compute_speed_factor(seg_idx, lead)
                lead.v_max = lead._v_max * factor
                lead.update(None, self.dt)
            for i in range(1, len(segment.vehicles)):
                veh = self.vehicles[segment.vehicles[i]]
                lead = self.vehicles[segment.vehicles[i-1]]
                factor = self._compute_speed_factor(seg_idx, veh)
                veh.v_max = veh._v_max * factor
                veh.update(lead, self.dt)

        # Check roads for out of bounds vehicle
        for segment in self.segments:
            # If road has no vehicles, continue
            if len(segment.vehicles) == 0: continue
            # If not
            vehicle_id = segment.vehicles[0]
            vehicle = self.vehicles[vehicle_id]
            # If first vehicle is out of road bounds
            if vehicle.x >= segment.get_length():
                # If vehicle has a next road
                if vehicle.current_road_index + 1 < len(vehicle.path):
                    # Update current road to next road
                    vehicle.current_road_index += 1
                    # Add it to the next road
                    next_road_index = vehicle.path[vehicle.current_road_index]
                    self.segments[next_road_index].vehicles.append(vehicle_id)
                # Reset vehicle properties
                vehicle.x = 0
                # In all cases, remove it from its road
                segment.vehicles.popleft() 

        # Update vehicle generators
        for gen in self.vehicle_generator:
            gen.update(self)
        # Increment time
        self.t += self.dt
        self.frame_count += 1

    def _update_events(self):
        self.segment_event_factors = {}
        self.segment_events_by_idx = {}
        active_ids = set()
        for ev in self.events:
            start = ev.get("start_time", 0)
            duration = ev.get("duration")
            end_time = ev.get("end_time", None)
            if end_time is None and duration is not None:
                end_time = start + duration

            is_active = self.t >= start and (end_time is None or self.t < end_time)
            ev["active"] = is_active
            if is_active:
                active_ids.add(ev.get("id"))

                seg_id = ev.get("segment_id")
                speed_factor = ev.get("speed_factor", 1.0)
                offset = ev.get("offset", 0.5)
                if seg_id is not None and seg_id in self.segment_by_id:
                    seg_idx = self.segment_by_id[seg_id]
                    current = self.segment_event_factors.get(seg_idx, 1.0)
                    # Apply the most restrictive (minimum) factor when multiple events overlap.
                    self.segment_event_factors[seg_idx] = min(current, speed_factor)

                    seg_len = self.segments[seg_idx].get_length() if seg_idx < len(self.segments) else 0
                    pos = offset * seg_len
                    bucket = self.segment_events_by_idx.setdefault(seg_idx, [])
                    bucket.append({"pos": pos, "factor": speed_factor, "event": ev})

        self.active_event_ids = active_ids

    def _update_junctions(self):
        """Advance traffic lights and rebuild segment->approach mapping."""
        self.segment_junctions = {}
        for jid, junc in self.junctions.items():
            for appr in junc.get("approaches", []):
                seg_id = appr.get("segment_id")
                if seg_id not in self.segment_by_id:
                    continue
                seg_idx = self.segment_by_id[seg_id]

                # Traffic light timing
                if appr.get("type") == "light":
                    green = appr.get("green", 30)
                    red = appr.get("red", 30)
                    phase_start = appr.setdefault("phase_start", 0.0)
                    phase = appr.setdefault("phase", "green")
                    elapsed = self.t - phase_start
                    if phase == "green" and elapsed >= green:
                        appr["phase"] = "red"
                        appr["phase_start"] = self.t
                    elif phase == "red" and elapsed >= red:
                        appr["phase"] = "green"
                        appr["phase_start"] = self.t

                bucket = self.segment_junctions.setdefault(seg_idx, [])
                bucket.append({
                    "junction_id": jid,
                    "offset": appr.get("offset", 0.5),
                    "type": appr.get("type", "yield"),
                    "phase": appr.get("phase", "green"),
                    "green": appr.get("green", 30),
                    "red": appr.get("red", 30)
                })

    def _compute_junction_factor(self, seg_idx, vehicle):
        """Compute slowdown/stop factor due to junction control and precedence."""
        approaches = self.segment_junctions.get(seg_idx, [])
        if not approaches:
            return 1.0

        seg = self.segments[seg_idx]
        seg_len = seg.get_length()
        factor = 1.0
        slow_dist = 40.0  # generic slowdown near junction
        light_slow_dist = 35.0  # start braking for a red light from this distance
        light_stop_dist = 6.0   # stop distance for a red light
        light_stop_factor = 0.0  # full stop at red when close
        yield_stop_factor = 0.1
        yield_factor = 0.2

        # Heading at position helper
        def heading_at(offset):
            off = min(max(offset, 0.0), 1.0)
            return seg.get_heading(off)

        for appr in approaches:
            offset = appr.get("offset", 0.5)
            ctrl_type = appr.get("type", "yield")
            dist_to = offset * seg_len - vehicle.x
            if dist_to < -2:
                continue  # already passed

            # Base slowdown approaching junction
            if 0 <= dist_to <= slow_dist:
                factor = min(factor, 0.6)

            # Control logic
            if ctrl_type == "light":
                phase = appr.get("phase", "green")
                if phase != "green" and dist_to >= 0:
                    if dist_to <= light_stop_dist:
                        factor = min(factor, light_stop_factor)
                    elif dist_to <= light_slow_dist:
                        factor = min(factor, 0.4)
            else:  # yield / merge priority-to-right
                if dist_to >= 0:
                    if self._has_vehicle_with_priority(appr, seg_idx, vehicle, dist_to, heading_at(offset)):
                        factor = min(factor, yield_stop_factor)
                    else:
                        factor = min(factor, yield_factor if dist_to < slow_dist else factor)

        return factor

    def _has_vehicle_with_priority(self, approach, seg_idx, vehicle, dist_to, heading):
        """Check if another approach at the same junction has priority (right-first/merge)."""
        jid = approach.get("junction_id")
        if jid not in self.junctions:
            return False
        junc = self.junctions[jid]
        conflict_dist = 20.0

        # Right-side check using heading difference
        def on_right(h_self, h_other):
            import math
            d = (h_other - h_self + math.pi) % (2*math.pi) - math.pi
            return 0 < d < math.pi/2

        for other in junc.get("approaches", []):
            other_seg_id = other.get("segment_id")
            if other_seg_id not in self.segment_by_id:
                continue
            other_idx = self.segment_by_id[other_seg_id]
            if other_idx == seg_idx:
                continue
            other_offset = other.get("offset", 0.5)
            other_seg = self.segments[other_idx]
            other_len = other_seg.get_length()

            # If other is light-controlled and red, it does not have priority now
            if other.get("type") == "light" and other.get("phase", "green") != "green":
                continue

            # Find lead vehicle on that segment, if any
            if len(other_seg.vehicles) == 0:
                continue
            other_lead = self.vehicles[other_seg.vehicles[0]]
            dist_other = other_offset * other_len - other_lead.x
            if dist_other < -2 or dist_other > conflict_dist:
                continue

            other_heading = other_seg.get_heading(other_offset)
            if on_right(heading, other_heading):
                return True

        return False

    def _compute_speed_factor(self, seg_idx, vehicle):
        """Return speed factor considering events ahead on current and next segment."""
        factor = 1.0
        seg_len = self.segments[seg_idx].get_length()
        remaining = max(0.0, seg_len - vehicle.x)

        # Events on current segment ahead within lookahead
        for ev in self.segment_events_by_idx.get(seg_idx, []):
            dist_ahead = ev["pos"] - vehicle.x
            if dist_ahead >= 0 and dist_ahead <= self.event_lookahead:
                factor = min(factor, ev["factor"])

        # Events on next segment within lookahead if vehicle is near end
        if remaining <= self.event_lookahead and vehicle.current_road_index + 1 < len(vehicle.path):
            next_idx = vehicle.path[vehicle.current_road_index + 1]
            next_len = self.segments[next_idx].get_length()
            for ev in self.segment_events_by_idx.get(next_idx, []):
                if remaining + ev["pos"] <= self.event_lookahead:
                    factor = min(factor, ev["factor"])

        # Junction slowdown and control
        factor = min(factor, self._compute_junction_factor(seg_idx, vehicle))

        return factor
