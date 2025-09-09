import json
import os
from cargosim.core.paths import USER_MAIN_CONFIG_FILE

def main():
    path = str(USER_MAIN_CONFIG_FILE)
    print("Config path:", path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("spoke_distances len:", len(data.get("spoke_distances", [])))
        sc = data.get("spoke_config", {})
        print("spoke_config max_spokes:", sc.get("max_spokes"))
        print("spoke_config distances len:", len(sc.get("spoke_distances", [])))
        if sc.get("spoke_distances"):
            print("first 5 distances:", sc["spoke_distances"][:5])
    else:
        print("No config file found.")

if __name__ == "__main__":
    main()

