import yaml


def read_settings(settings_path="settings.yaml"):
    try:
        with open(settings_path, "r") as file:
            settings_data = yaml.safe_load(file)
    except (FileNotFoundError, yaml.YAMLError):
        settings_data = None

    if settings_data is None:
        settings_data = {
            'cache': {
                'netbox': {
                    'roles': {
                        'days': 1, 'hours': 0, 'minutes': 0
                    },
                    'devices': {
                        'days': 1, 'hours': 0, 'minutes': 0
                    }
                },
                'pfsense': {
                    'config': {
                        'days': 0, 'hours': 1, 'minutes': 0
                    }
                }
            }
        }
        with open(settings_path, "w") as file:
            yaml.dump(settings_data, file)

    return settings_data
