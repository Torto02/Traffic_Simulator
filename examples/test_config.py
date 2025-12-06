import trafficSimulator as ts
from pathlib import Path


if __name__ == "__main__":
    # Choose which config to run: "config_sample.json" or "config_city.json"
    config_name = "config_sample.json"
    config_path = Path(__file__).with_name(config_name)

    sim, ui_cfg = ts.load_simulation_from_json(config_path)

    win = ts.Window(sim, ui_cfg)
    win.show()
