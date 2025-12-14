import dearpygui.dearpygui as dpg
from math import cos, sin


class Window:
    def __init__(self, simulation, ui_config=None):
        self.simulation = simulation

        ui_config = ui_config or {}
        self.viewport_title = ui_config.get("title", "TrafficSimulator")
        self.viewport_width = ui_config.get("width", 1280)
        self.viewport_height = ui_config.get("height", 720)
        self.background_color = tuple(ui_config.get("background_color", (250, 250, 250)))

        self.zoom = 7
        self.offset = (0, 0)
        self.speed = 1

        # Layer visibility
        self.show_environment = True
        self.show_events = True
        self.show_arrows = True

        self.is_running = False

        self.is_dragging = False
        self.old_offset = (0, 0)
        self.zoom_speed = 1

        self.setup()
        self.setup_themes()
        self.create_windows()
        self.create_handlers()
        self.resize_windows()

    def setup(self):
        dpg.create_context()
        dpg.create_viewport(title=self.viewport_title, width=self.viewport_width, height=self.viewport_height)
        dpg.setup_dearpygui()

    def setup_themes(self):
        with dpg.theme() as global_theme:

            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core)
                # dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, (8, 6), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Button, (90, 90, 95))
                dpg.add_theme_color(dpg.mvThemeCol_Header, (0, 91, 140))
            with dpg.theme_component(dpg.mvInputInt):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (90, 90, 95), category=dpg.mvThemeCat_Core)
            #     dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)

        dpg.bind_theme(global_theme)

        # dpg.show_style_editor()

        with dpg.theme(tag="RunButtonTheme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (5, 150, 18))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (12, 207, 23))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (2, 120, 10))

        with dpg.theme(tag="StopButtonTheme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (150, 5, 18))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (207, 12, 23))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (120, 2, 10))


    def create_windows(self):
        dpg.add_window(
            tag="MainWindow",
            label="Simulation",
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True
        )
        
        dpg.add_draw_node(tag="OverlayCanvas", parent="MainWindow")
        dpg.add_draw_node(tag="Canvas", parent="MainWindow")

        with dpg.window(
            tag="ControlsWindow",
            label="Controls",
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True
        ):
            with dpg.collapsing_header(label="Simulation Control", default_open=True):

                with dpg.group(horizontal=True):
                    dpg.add_button(label="Run", tag="RunStopButton", callback=self.toggle)
                    dpg.add_button(label="Next frame", callback=self.simulation.update)

                dpg.add_slider_int(tag="SpeedInput", label="Speed", min_value=1, max_value=100,default_value=1, callback=self.set_speed)
            
            with dpg.collapsing_header(label="Simulation Status", default_open=True):

                with dpg.table(header_row=False):
                    dpg.add_table_column()
                    dpg.add_table_column()
                    
                    with dpg.table_row():
                        dpg.add_text("Status:")
                        dpg.add_text("_", tag="StatusText")

                    with dpg.table_row():
                        dpg.add_text("Time:")
                        dpg.add_text("_s", tag="TimeStatus")

                    with dpg.table_row():
                        dpg.add_text("Frame:")
                        dpg.add_text("_", tag="FrameStatus")

                    with dpg.table_row():
                        dpg.add_text("Vehicles:")
                        dpg.add_text("_", tag="VehicleCount")

                    with dpg.table_row():
                        dpg.add_text("Active events:")
                        dpg.add_text("_", tag="ActiveEvents")
            
            
            with dpg.collapsing_header(label="Camera Control", default_open=True):
    
                dpg.add_slider_float(tag="ZoomSlider", label="Zoom", min_value=0.1, max_value=100, default_value=self.zoom,callback=self.set_offset_zoom)            
                with dpg.group():
                    dpg.add_slider_float(tag="OffsetXSlider", label="X Offset", min_value=-100, max_value=100, default_value=self.offset[0], callback=self.set_offset_zoom)
                    dpg.add_slider_float(tag="OffsetYSlider", label="Y Offset", min_value=-100, max_value=100, default_value=self.offset[1], callback=self.set_offset_zoom)

            with dpg.collapsing_header(label="Layers", default_open=True):
                dpg.add_checkbox(label="Show environment", default_value=self.show_environment, callback=self.toggle_environment, tag="EnvToggle")
                dpg.add_checkbox(label="Show events", default_value=self.show_events, callback=self.toggle_events, tag="EventsToggle")
                dpg.add_checkbox(label="Show arrows", default_value=self.show_arrows, callback=self.toggle_arrows, tag="ArrowsToggle")

    def resize_windows(self):
        width = dpg.get_viewport_width()
        height = dpg.get_viewport_height()

        dpg.set_item_width("ControlsWindow", 300)
        dpg.set_item_height("ControlsWindow", height-38)
        dpg.set_item_pos("ControlsWindow", (0, 0))

        dpg.set_item_width("MainWindow", width-315)
        dpg.set_item_height("MainWindow", height-38)
        dpg.set_item_pos("MainWindow", (300, 0))

    def create_handlers(self):
        with dpg.handler_registry():
            dpg.add_mouse_down_handler(callback=self.mouse_down)
            dpg.add_mouse_drag_handler(callback=self.mouse_drag)
            dpg.add_mouse_release_handler(callback=self.mouse_release)
            dpg.add_mouse_wheel_handler(callback=self.mouse_wheel)
        dpg.set_viewport_resize_callback(self.resize_windows)

    def update_panels(self):
        # Update status text
        if self.is_running:
            dpg.set_value("StatusText", "Running")
            dpg.configure_item("StatusText", color=(0, 255, 0))
        else:
            dpg.set_value("StatusText", "Stopped")
            dpg.configure_item("StatusText", color=(255, 0, 0))
        
        # Update time and frame text
        dpg.set_value("TimeStatus", f"{self.simulation.t:.2f}s")
        dpg.set_value("FrameStatus", self.simulation.frame_count)

        # Update counts
        dpg.set_value("VehicleCount", len(self.simulation.vehicles))
        active_events = len(getattr(self.simulation, "active_event_ids", []))
        dpg.set_value("ActiveEvents", active_events)

        


    def mouse_down(self):
        if not self.is_dragging:
            if dpg.is_item_hovered("MainWindow"):
                self.is_dragging = True
                self.old_offset = self.offset
        
    def mouse_drag(self, sender, app_data):
        if self.is_dragging:
            self.offset = (
                self.old_offset[0] + app_data[1]/self.zoom,
                self.old_offset[1] - app_data[2]/self.zoom
            )

    def mouse_release(self):
        self.is_dragging = False

    def mouse_wheel(self, sender, app_data):
        if dpg.is_item_hovered("MainWindow"):
            self.zoom_speed = 1 + 0.01*app_data

    def update_inertial_zoom(self, clip=0.005):
        if self.zoom_speed != 1:
            self.zoom *= self.zoom_speed
            self.zoom_speed = 1 + (self.zoom_speed - 1) / 1.05
        if abs(self.zoom_speed - 1) < clip:
            self.zoom_speed = 1

    def update_offset_zoom_slider(self):
        dpg.set_value("ZoomSlider", self.zoom)
        dpg.set_value("OffsetXSlider", self.offset[0])
        dpg.set_value("OffsetYSlider", self.offset[1])

    def set_offset_zoom(self):
        self.zoom = dpg.get_value("ZoomSlider")
        self.offset = (dpg.get_value("OffsetXSlider"), dpg.get_value("OffsetYSlider"))

    def set_speed(self):
        self.speed = dpg.get_value("SpeedInput")


    def to_screen(self, x, y):
        return (
            self.canvas_width/2 + (x + self.offset[0] ) * self.zoom,
            self.canvas_height/2 - (y + self.offset[1]) * self.zoom
        )

    def to_world(self, x, y):
        return (
            (x - self.canvas_width/2) / self.zoom - self.offset[0],
            -(y - self.canvas_height/2) / self.zoom - self.offset[1]
        )
    
    @property
    def canvas_width(self):
        return dpg.get_item_width("MainWindow")

    @property
    def canvas_height(self):
        return dpg.get_item_height("MainWindow")


    def draw_bg(self, color=None):
        bg = color if color is not None else self.background_color
        dpg.draw_rectangle(
            (-10, -10),
            (self.canvas_width+10, self.canvas_height+10), 
            thickness=0,
            fill=bg,
            parent="OverlayCanvas"
        )

    def draw_axes(self, opacity=80):
        x_center, y_center = self.to_screen(0, 0)
        
        dpg.draw_line(
            (-10, y_center),
            (self.canvas_width+10, y_center),
            thickness=2, 
            color=(0, 0, 0, opacity),
            parent="OverlayCanvas"
        )
        dpg.draw_line(
            (x_center, -10),
            (x_center, self.canvas_height+10),
            thickness=2,
            color=(0, 0, 0, opacity),
            parent="OverlayCanvas"
        )

    def draw_grid(self, unit=10, opacity=50):
        x_start, y_start = self.to_world(0, 0)
        x_end, y_end = self.to_world(self.canvas_width, self.canvas_height)

        n_x = int(x_start / unit)
        n_y = int(y_start / unit)
        m_x = int(x_end / unit)+1
        m_y = int(y_end / unit)+1

        for i in range(n_x, m_x):
            dpg.draw_line(
                self.to_screen(unit*i, y_start - 10/self.zoom),
                self.to_screen(unit*i, y_end + 10/self.zoom),
                thickness=1,
                color=(0, 0, 0, opacity),
                parent="OverlayCanvas"
            )

        for i in range(n_y, m_y):
            dpg.draw_line(
                self.to_screen(x_start - 10/self.zoom, unit*i),
                self.to_screen(x_end + 10/self.zoom, unit*i),
                thickness=1,
                color=(0, 0, 0, opacity),
                parent="OverlayCanvas"
            )

    def draw_segments(self):
        for segment in self.simulation.segments:
            color = segment.color if hasattr(segment, "color") else (180, 180, 220)
            thickness = (segment.width if hasattr(segment, "width") else 3.5) * self.zoom
            dpg.draw_polyline(segment.points, color=color, thickness=thickness, parent="Canvas")

            # Direction hint: arrow along the segment centerline to show flow.
            if getattr(segment, "direction_hint", True) and len(segment.points) >= 2:
                if not self.show_arrows:
                    continue
                mid_point = segment.get_point(0.5)
                heading = -segment.get_heading(0.5)  # invert to compensate flipped Y scale
                arrow_len = max(2.5, (segment.width if hasattr(segment, "width") else 3.5) * 1.1)
                dx = cos(heading) * arrow_len
                dy = sin(heading) * arrow_len
                start = (mid_point[0] - dx * 0.5, mid_point[1] - dy * 0.5)
                end = (mid_point[0] + dx * 0.5, mid_point[1] + dy * 0.5)
                dpg.draw_arrow(start, end, thickness=0, size=arrow_len*0.35, color=(0, 0, 0, 80), parent="Canvas")

    def draw_vehicles(self):
        for segment in self.simulation.segments:
            for vehicle_id in segment.vehicles:
                vehicle = self.simulation.vehicles[vehicle_id]
                progress = vehicle.x / segment.get_length()

                position = segment.get_point(progress)
                heading = -segment.get_heading(progress)  # compensate Y flip

                node = dpg.add_draw_node(parent="Canvas")

                color = getattr(vehicle, "color", (0, 0, 255))
                thickness = 1.2 * self.zoom
                half_len = vehicle.l / 2
                half_width = vehicle.l / 4

                # Simple shapes per vehicle class; renderer can be extended later.
                if vehicle.shape == "triangle":
                    tip = (half_len, 0)
                    rear_left = (-half_len, half_width)
                    rear_right = (-half_len, -half_width)
                    dpg.draw_triangle(tip, rear_left, rear_right, color=color, fill=color, thickness=thickness, parent=node)
                elif vehicle.shape == "circle":
                    dpg.draw_circle(center=(0, 0), radius=half_len * 0.6, color=color, fill=color, thickness=thickness, parent=node)
                else:  # default rectangle
                    dpg.draw_rectangle((-half_len, -half_width), (half_len, half_width), color=color, fill=color, thickness=thickness, parent=node)

                translate = dpg.create_translation_matrix(position)
                rotate = dpg.create_rotation_matrix(heading, [0, 0, 1])
                dpg.apply_transform(node, translate*rotate)

    def draw_events(self):
        if not self.show_events:
            return
        for ev in getattr(self.simulation, "events", []):
            if not ev.get("active", False):
                continue

            ev_type = ev.get("type", "event")
            color = tuple(ev.get("color", {
                "accident": (220, 20, 60),
                "works": (255, 140, 0),
                "animal": (139, 69, 19),
            }.get(ev_type, (0, 0, 0))))

            pos = ev.get("position")
            if pos is None and ev.get("segment_id") is not None:
                seg_id = ev.get("segment_id")
                offset = ev.get("offset", 0.5)
                seg_idx = self.simulation.segment_by_id.get(seg_id)
                if seg_idx is not None:
                    seg = self.simulation.segments[seg_idx]
                    pos = seg.get_point(offset)
            if pos is None:
                pos = (0, 0)

            size = ev.get("size", 3)
            parent = "Canvas"

            if ev_type == "accident":
                dpg.draw_circle(pos, radius=size*0.6, color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)
                dpg.draw_line((pos[0]-size, pos[1]-size), (pos[0]+size, pos[1]+size), color=(255,255,255), thickness=max(1.0, 0.8*self.zoom), parent=parent)
                dpg.draw_line((pos[0]-size, pos[1]+size), (pos[0]+size, pos[1]-size), color=(255,255,255), thickness=max(1.0, 0.8*self.zoom), parent=parent)
            elif ev_type == "works":
                dpg.draw_triangle((pos[0], pos[1]-size), (pos[0]-size, pos[1]+size), (pos[0]+size, pos[1]+size), color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)
                dpg.draw_line((pos[0]-size*0.6, pos[1]+size*0.3), (pos[0]+size*0.6, pos[1]+size*0.3), color=(255, 215, 0), thickness=max(1.0, 0.8*self.zoom), parent=parent)
            elif ev_type == "animal":
                dpg.draw_circle(pos, radius=size*0.6, color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)
                dpg.draw_circle((pos[0]-size*0.6, pos[1]-size*0.4), radius=size*0.25, color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)
                dpg.draw_circle((pos[0]+size*0.6, pos[1]-size*0.4), radius=size*0.25, color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)
            else:
                dpg.draw_circle(pos, radius=size*0.5, color=color, fill=color, thickness=max(1.0, 0.8*self.zoom), parent=parent)

    def draw_junctions(self):
        # Render traffic lights (if any) at junction approaches
        for junc in getattr(self.simulation, "junctions", {}).values():
            for appr in junc.get("approaches", []):
                if appr.get("type") != "light":
                    continue
                seg_id = appr.get("segment_id")
                if seg_id not in self.simulation.segment_by_id:
                    continue
                seg_idx = self.simulation.segment_by_id[seg_id]
                seg = self.simulation.segments[seg_idx]
                offset = appr.get("offset", 0.5)
                pos = seg.get_point(offset)
                phase = appr.get("phase", "green")
                color = (0, 180, 0) if phase == "green" else (200, 40, 40)
                size = 1.5
                dpg.draw_circle(pos, radius=size*self.zoom, color=color, fill=color, thickness=1.0*self.zoom, parent="Canvas")

    def draw_environment(self):
        if not self.show_environment:
            return
        for obj in getattr(self.simulation, "environment", []):
            obj_type = obj.get("type", "marker")
            pos = obj.get("position", (0, 0))
            color = tuple(obj.get("color", (60, 60, 60)))
            size = obj.get("size", 3)
            parent = "Canvas"

            if obj_type == "tree":
                trunk_h = size * self.zoom
                crown_r = size * 1.2 * self.zoom
                # trunk
                dpg.draw_line((pos[0], pos[1]), (pos[0], pos[1] + trunk_h), color=(120, 72, 0), thickness=1.2*self.zoom, parent=parent)
                # crown
                dpg.draw_circle((pos[0], pos[1] + trunk_h), radius=crown_r, color=(34, 139, 34), fill=(34, 139, 34), thickness=1.2*self.zoom, parent=parent)
            elif obj_type == "lamp":
                h = size * 1.5 * self.zoom
                dpg.draw_line((pos[0], pos[1]), (pos[0], pos[1] + h), color=color, thickness=1.0*self.zoom, parent=parent)
                dpg.draw_circle((pos[0], pos[1] + h), radius=0.4*h, color=(255, 215, 0), fill=(255, 215, 0), thickness=1.0*self.zoom, parent=parent)
            elif obj_type == "building":
                w = size * 2 * self.zoom
                h = size * 2 * self.zoom
                dpg.draw_rectangle((pos[0]-w/2, pos[1]-h/2), (pos[0]+w/2, pos[1]+h/2), color=color, fill=color, thickness=1.0*self.zoom, parent=parent)
            elif obj_type == "rsu":
                r = size * 0.8 * self.zoom
                dpg.draw_circle(pos, radius=r, color=(0, 191, 255), fill=(0, 191, 255), thickness=1.0*self.zoom, parent=parent)
                dpg.draw_circle(pos, radius=r*1.8, color=(0, 191, 255, 80), thickness=1.0*self.zoom, parent=parent)
            elif obj_type == "vru":
                r = size * 0.6 * self.zoom
                dpg.draw_circle(pos, radius=r, color=(220, 20, 60), fill=(220, 20, 60), thickness=1.0*self.zoom, parent=parent)
            else:  # generic marker
                r = size * self.zoom
                dpg.draw_circle(pos, radius=r, color=color, fill=color, thickness=1.0*self.zoom, parent=parent)

    def apply_transformation(self):
        screen_center = dpg.create_translation_matrix([self.canvas_width/2, self.canvas_height/2, -0.01])
        translate = dpg.create_translation_matrix(self.offset)
        scale = dpg.create_scale_matrix([self.zoom, -self.zoom])
        dpg.apply_transform("Canvas", screen_center*scale*translate)


    def render_loop(self):
        # Events
        self.update_inertial_zoom()
        self.update_offset_zoom_slider()

        # Remove old drawings
        dpg.delete_item("OverlayCanvas", children_only=True)
        dpg.delete_item("Canvas", children_only=True)
        
        # New drawings
        self.draw_bg()
        self.draw_axes()
        self.draw_grid(unit=10)
        self.draw_grid(unit=50)
        self.draw_segments()
        self.draw_environment()
        self.draw_events()
        self.draw_junctions()
        self.draw_vehicles()

        # Apply transformations
        self.apply_transformation()

        # Update panels
        self.update_panels()

        # Update simulation
        if self.is_running:
            self.simulation.run(self.speed)

    def show(self):
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            self.render_loop()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

    def run(self):
        self.is_running = True
        dpg.set_item_label("RunStopButton", "Stop")
        dpg.bind_item_theme("RunStopButton", "StopButtonTheme")

    def stop(self):
        self.is_running = False
        dpg.set_item_label("RunStopButton", "Run")
        dpg.bind_item_theme("RunStopButton", "RunButtonTheme")

    def toggle(self):
        if self.is_running: self.stop()
        else: self.run()

    # Toggle handlers
    def toggle_environment(self):
        self.show_environment = dpg.get_value("EnvToggle")

    def toggle_events(self):
        self.show_events = dpg.get_value("EventsToggle")

    def toggle_arrows(self):
        self.show_arrows = dpg.get_value("ArrowsToggle")