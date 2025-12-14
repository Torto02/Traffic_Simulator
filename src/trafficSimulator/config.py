"""JSON configuration loader for simulations and GUI settings."""

import json
from pathlib import Path
from typing import Tuple, Dict, Any, List
import math

from .core.simulation import Simulation
from .core.vehicle import Vehicle
from .core.vehicle_generator import VehicleGenerator
from .core.geometry.segment import Segment
from .core.geometry.quadratic_curve import QuadraticCurve
from .core.geometry.cubic_curve import CubicCurve


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file and return it as a dictionary."""
    path_obj = Path(path)
    with path_obj.open("r", encoding="utf-8") as f:
        return json.load(f)


def _tuple_point(pt: List[float]) -> Tuple[float, float]:
    return tuple(pt) if pt is not None else pt


def _clean_metadata(cfg: Dict[str, Any]) -> Dict[str, Any]:
    keys = ["id", "category", "material", "max_speed", "width", "color", "direction_hint"]
    md = {k: cfg.get(k) for k in keys if cfg.get(k) is not None}
    if "color" in md and isinstance(md["color"], list):
        md["color"] = tuple(md["color"])
    return md


def build_simulation(config: Dict[str, Any]) -> Simulation:
    """Build a Simulation object from a configuration dictionary."""
    sim = Simulation()

    def _endpoint(seg_id: str, at_end: bool) -> Tuple[float, float]:
        if seg_id not in sim.segment_by_id:
            raise ValueError(f"Cannot connect: segment id '{seg_id}' not found")
        seg = sim.segments[sim.segment_by_id[seg_id]]
        return seg.points[-1] if at_end else seg.points[0]

    def _heading(seg_id: str, at_end: bool) -> float:
        if seg_id not in sim.segment_by_id:
            raise ValueError(f"Cannot get heading: segment id '{seg_id}' not found")
        seg = sim.segments[sim.segment_by_id[seg_id]]
        offset = 0.999 if at_end else 0.0
        return seg.get_heading(offset)

    def _auto_quadratic_control(
        start: Tuple[float, float],
        end: Tuple[float, float],
        ref_seg: str,
        scale: float,
        lateral: float,
    ) -> Tuple[float, float]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            return start

        if ref_seg:
            heading = _heading(ref_seg, at_end=True)
            dir_vec = (math.cos(heading), math.sin(heading))
            # Normal for gentle outward bend
            normal_vec = (-dir_vec[1], dir_vec[0])
        else:
            dir_vec = (dx / dist, dy / dist)
            normal_vec = (-dir_vec[1], dir_vec[0])

        ctrl = (
            start[0] + dir_vec[0] * dist * scale + normal_vec[0] * dist * lateral,
            start[1] + dir_vec[1] * dist * scale + normal_vec[1] * dist * lateral,
        )
        return ctrl

    # Segments
    for seg in config.get("segments", []):
        seg_type = seg.get("type", "segment").lower()
        md = _clean_metadata(seg)

        if seg_type == "quadratic":
            start = _tuple_point(seg.get("start"))
            end = _tuple_point(seg.get("end"))

            # Snap to other segments if requested
            connect_from = seg.get("connect_from")
            connect_to = seg.get("connect_to")
            connect_to_end = seg.get("connect_to_end", False)
            if connect_from:
                start = _endpoint(connect_from, at_end=True)
            if connect_to:
                end = _endpoint(connect_to, at_end=bool(connect_to_end))

            if start is None or end is None:
                raise ValueError(f"Quadratic segment '{seg.get('id')}' requires start/end or connect_from/connect_to")

            control = _tuple_point(seg.get("control"))
            control_scale = seg.get("control_scale", 0.35)
            if seg.get("auto_control", False) or control is None:
                control_lateral = seg.get("control_offset", 0.25)
                control = _auto_quadratic_control(start, end, connect_from, control_scale, control_lateral)

            sim.create_quadratic_bezier_curve(start, control, end, **md)
        elif seg_type == "cubic":
            sim.create_cubic_bezier_curve(
                _tuple_point(seg.get("start")),
                _tuple_point(seg.get("control_1")),
                _tuple_point(seg.get("control_2")),
                _tuple_point(seg.get("end")),
                **md,
            )
        else:
            points = seg.get("points", [])
            # Accept shorthand start/end for straight segments
            if (not points) and seg.get("start") is not None and seg.get("end") is not None:
                points = [seg.get("start"), seg.get("end")]
            points = [_tuple_point(p) for p in points]
            if not points:
                raise ValueError(f"Segment '{seg.get('id', '<unnamed>')}' has no points/start/end defined")
            sim.create_segment(*points, **md)

    # Vehicles
    for veh in config.get("vehicles", []):
        sim.create_vehicle(**veh)

    # Vehicle generators
    for gen in config.get("vehicle_generators", []):
        vehicles = gen.get("vehicles", [])
        # Ensure tuples for weights/config pairs if provided as lists.
        gen["vehicles"] = [(v[0], v[1]) for v in vehicles]
        sim.create_vehicle_generator(**gen)

    # Environment objects
    for obj in config.get("environment", []):
        # Normalize color tuple if provided as list
        if "color" in obj and isinstance(obj["color"], list):
            obj["color"] = tuple(obj["color"])
        sim.add_environment_object(obj)

    # Events
    for ev in config.get("events", []):
        if "color" in ev and isinstance(ev["color"], list):
            ev["color"] = tuple(ev["color"])
        sim.add_event(ev)

    # Junctions
    for junc in config.get("junctions", []):
        sim.add_junction(junc)

    return sim


def load_simulation_from_json(path: str) -> Tuple[Simulation, Dict[str, Any]]:
    """
    Convenience helper: load JSON config, build Simulation, and return UI config.

    Returns (simulation, ui_config_dict).
    """
    cfg = load_config(path)
    sim = build_simulation(cfg)
    ui_cfg = cfg.get("ui", {})
    return sim, ui_cfg
