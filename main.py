import os
from dotenv import load_dotenv
from netaddr import IPNetwork
from prettytable import PrettyTable
import yaml

from modules.rule.check import check_rule_match
from modules.rule.format import format_rule
from modules.updater import check_update
from modules.service.netbox import NetboxAPI
from modules.service.pfsense import PFSense
from modules.input_query import setup_readline, parse_search_query

# Fix Ctrl+C for IntelliJ IDEA
try:
    from console_thrift import KeyboardInterruptException as KeyboardInterrupt
except ImportError:
    pass

__GITHUB_UPDATE_URL = 'https://raw.githubusercontent.com/Reydan46/RulesTrackerPF/master/'
__CURRENT_VERSION = '1.02'
__COMMANDS = ['pf', 'act', 'desc', 'src', 'dst', 'port']


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


if __name__ == '__main__':
    check_update(__GITHUB_UPDATE_URL, __CURRENT_VERSION)

    settings = read_settings()

    router_devices = []
    # Загрузка переменных окружения из .env
    load_dotenv(dotenv_path='.env')
    # Установка настроек
    NetboxAPI.settings = settings
    # Создание подключения с NetBox
    if NetboxAPI.create_connection():
        # Получение ролей устройств с NetBox
        if NetboxAPI.get_roles() and 'Router' in NetboxAPI.roles:
            # Получение устройств с ролью router (в нашем случае это все pfSense)
            router_devices = NetboxAPI.get_devices(
                role=NetboxAPI.roles['Router'])

    PFSense.settings = settings
    PFs = []
    for router in router_devices:
        pf = PFSense(
            ip=router.primary_ip4.address.split('/')[0],
            name=router.name
        )
        pf.run()
        PFs.append(pf)

    # Инициализация автозаполнения команд
    setup_readline(__COMMANDS)
    # Поиск
    while True:
        try:
            query = input('Enter query: ')
            parsed_query, parsed_success = parse_search_query(query, __COMMANDS)

            os.system('cls' if os.name == 'nt' else 'clear')
        except KeyboardInterrupt:
            print('\nProgram terminated by user')
            break
        if not parsed_success:
            input('Press Enter to continue...')
            continue

        header = ["PF Name", "Num", "Tracker", "Action", "Floating", "Interface", "Source", "Destination", "Ports",
                  "Gateway", "Description"]
        table = PrettyTable(header)
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Action"] = 7
        table.max_width["Description"] = 30
        table.max_width["Source"] = 20
        table.max_width["Destination"] = 20

        for pf in PFs:
            num = 0
            filtered_rules = []

            # Определяем домашний ли pf по отношению к искомому ip
            if parsed_query['src']:
                home_pf = False
                for interface in pf.config.interfaces:
                    ip_network_string = interface.get_ip_obj()
                    if ip_network_string and IPNetwork(parsed_query['src']['value']) in IPNetwork(ip_network_string):
                        home_pf = True
                        break
            else:
                # Если source не указан - считаем домашними все PFSense
                home_pf = True

            # Обработка правил floating (quick)
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)' and check_rule_match(rule, parsed_query, num, pf, table,
                                                                            home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил интерфейсов
            for rule in pf.config.filter:
                if rule.floating == 'no' and check_rule_match(rule, parsed_query, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил floating (без quick)
            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '' and check_rule_match(rule, parsed_query, num, pf, table,
                                                                                    home_pf):
                    filtered_rules.append(rule)
                    num += 1

            pf.config.get_html(custom_rules=filtered_rules,
                               save=True, filename=f"report\\html\\{pf.name}.html")

            os.makedirs("report\\csv", exist_ok=True)
            with open(f"report\\csv\\{pf.name}.csv", "w") as f:
                f.write(';'.join(header) + '\n')
                for rule in filtered_rules:
                    f.write(';'.join(format_rule(pf, rule, num, csv=True)) + '  \n')

            if filtered_rules and pf != PFs[-1]:
                table.add_row(["-" * len(column) for column in table.field_names])

        print(table)
