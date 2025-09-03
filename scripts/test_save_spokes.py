from cargosim.core.configuration_manager import get_configuration_manager
from cargosim.core.config import load_config

def main():
    cm = get_configuration_manager()
    config = {
        'variable_spoke_count': True,
        'max_spokes': 12,
        'spoke_distances': [500.0]*12,
    }
    print('Saving spoke_config with', len(config['spoke_distances']), 'spokes')
    print('Result:', cm.save_spoke_config(config))
    cfg = load_config()
    print('Saved len(spoke_distances)=', len(cfg.spoke_distances))
    sc = cfg.spoke_config or {}
    print('Saved spoke_config max_spokes=', sc.get('max_spokes'))
    print('Saved spoke_config len=', len(sc.get('spoke_distances', [])))

if __name__ == '__main__':
    main()

