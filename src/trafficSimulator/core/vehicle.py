import uuid
import numpy as np


# Styling presets by vehicle class for consistent rendering.
VEHICLE_CLASS_STYLES = {
    "vehicle": {"color": (0, 0, 255), "shape": "rect"},
    "truck": {"color": (255, 165, 0), "shape": "rect"},
    "bus": {"color": (0, 128, 0), "shape": "rect"},
    "tank": {"color": (128, 128, 128), "shape": "rect"},
    "ev": {"color": (0, 191, 255), "shape": "rect"},
}

class Vehicle:
    def __init__(self, config={}):
        # Set default configuration
        self.set_default_config()

        # Update configuration
        for attr, val in config.items():
            setattr(self, attr, val)

        # Harmonize style defaults based on vehicle_class when explicit values are missing
        self.apply_style_defaults()

        # Calculate properties
        self.init_properties()
        
    def set_default_config(self):    
        self.id = uuid.uuid4()

        # Physical parameters
        self.l = 4
        self.s0 = 4
        self.T = 1
        self.v_max = 16.6
        self.a_max = 1.44
        self.b_max = 4.61

        # Path info
        self.path = []
        self.current_road_index = 0

        # Kinematics
        self.x = 0
        self.v = 0
        self.a = 0
        self.stopped = False

        # Classification and rendering hints
        self.vehicle_class = "vehicle"
        self.color = None
        self.shape = None  # supported: rect, triangle, circle (renderer can extend)

        # Telemetry/OBU-related fields (placeholders for future logic)
        self.co2_emission = None  # g/km or similar
        self.engine_type = None   # e.g., electric, combustion, hybrid, hydrogen
        self.rpm = None
        self.ac_temp = None
        self.ambient_light = None
        self.fog_lights = False
        self.rain_sensor = False

    def apply_style_defaults(self):
        """Apply color/shape defaults from class presets when not explicitly set."""
        preset = VEHICLE_CLASS_STYLES.get(self.vehicle_class, {})
        if self.color is None:
            self.color = preset.get("color", (0, 0, 255))
        if self.shape is None:
            self.shape = preset.get("shape", "rect")

    def init_properties(self):
        self.sqrt_ab = 2*np.sqrt(self.a_max*self.b_max)
        self._v_max = self.v_max

    def update(self, lead, dt):
        # Update position and velocity
        if self.v + self.a*dt < 0:
            self.x -= 1/2*self.v*self.v/self.a
            self.v = 0
        else:
            self.v += self.a*dt
            self.x += self.v*dt + self.a*dt*dt/2
        
        # Update acceleration
        alpha = 0
        if lead:
            delta_x = lead.x - self.x - lead.l
            delta_v = self.v - lead.v

            alpha = (self.s0 + max(0, self.T*self.v + delta_v*self.v/self.sqrt_ab)) / delta_x

        self.a = self.a_max * (1-(self.v/self.v_max)**4 - alpha**2)

        if self.stopped: 
            self.a = -self.b_max*self.v/self.v_max
        