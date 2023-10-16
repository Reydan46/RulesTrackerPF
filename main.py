from netaddr import IPAddress, IPNetwork
from dotenv import load_dotenv

from colorama import Fore
from prettytable import PrettyTable

from netbox import NetboxAPI
from pfsense import PFSense


def add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table, tmp_direction):
    str_source = '\n'.join(
        [f"{Fore.RED if inp_rule.source_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.source_obj['direction']])
    str_destination = '\n'.join(
        [f"{Fore.RED if inp_rule.destination_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.destination_obj['direction']])
    str_ports = ''.join([cnf['value'] for cnf in inp_rule.destination if cnf['type'] == 'port'])

    inp_table.add_row([
        inp_pf.name,
        f"{inp_num + 1}",
        inp_rule.tracker,
        inp_rule.type,
        inp_rule.floating_full,
        inp_rule.descr_full,
        inp_rule.gateway_full,
        str_source,
        str_destination,
        str_ports,
        tmp_direction
    ])


def check_rule(inp_rule, inp_ip, inp_num, inp_pf, inp_table, home):
    direction=''
    # Пропуск отключённых правил
    if rule.disabled != 'no':
        return False

    ### Проверка источника
    # Флаг найденного правила
    find_rule = False
    for source in inp_rule.source_obj['direction']:
        ip_matched, network = source.ip_in_range(inp_ip)
        if ip_matched:
            if home:
                find_rule = True
                break
            else:
                if network != '0.0.0.0/0':
                    find_rule = True
                    break
    # Если нужно НЕ[алиас|сеть] в источнике
    if inp_rule.source_obj['inverse']:
        # Инвертируем результат поиска
        find_rule = not find_rule

    ### Временно
    if find_rule:
        direction='src'

    ### Проверка назначения
    # Если в источнике не было найдено правила
    if not find_rule:
        # Обходим все сети в назначении
        for dest in inp_rule.destination_obj['direction']:
            # Проверяем вхождение введённого ip в сеть
            ip_matched, network = dest.ip_in_range(inp_ip)
            # Если ip входит в сеть
            if ip_matched:
                # Поднимаем флаг поиска
                find_rule = True
                break
        # Если нужно НЕ[алиас|сеть] в назначении
        if inp_rule.destination_obj['inverse']:
            # Инвертируем результат поиска
            find_rule = not find_rule

        ### Временно
        if find_rule:
            direction='dst'

    ### Занесение найденного правила в таблицу
    # Если поиск правила был успешен
    if find_rule:
        # Заносим его в таблицу
        add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table, direction)

    return find_rule


if __name__ == '__main__':
    router_devices = []

    # Загрузка переменных окружения из .env
    load_dotenv(dotenv_path='.env')
    # Создание подключения с NetBox
    if NetboxAPI.create_connection():
        # Получение ролей устройств с NetBox
        if NetboxAPI.get_roles() and 'Router' in NetboxAPI.roles:
            # Получение устройств с ролью router (в нашем случае это все pfSense)
            router_devices = NetboxAPI.get_devices(role=NetboxAPI.roles['Router'])

    PFs = []
    for router in router_devices:
        # if True:
        #     router = router_devices[0]
        pf = PFSense(
            ip=router.primary_ip4.address.split('/')[0],
            name=router.name
        )
        pf.run()
        PFs.append(pf)

    # Search Console
    while True:
        try:
            ip = input('Enter IP: ')
        except Exception:
            print('Program terminated by user')
            break

        table = PrettyTable(
            ["PF Name", "Num", "Tracker", "Action", "Floating", "Description", "Gateway", "Source", "Destination",
             "Ports","Found IN"])
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Description"] = 30

        for pf in PFs:
            num = 0
            filtered_rules = []

            home_pf = False
            for interface in pf.config.interfaces:
                ip_network_string = interface.get_ip_obj()
                if ip_network_string:
                    ip_network = IPNetwork(ip_network_string)
                    if IPAddress(ip) in ip_network:
                        home_pf = True
                        break

            if num > 0:
                table.add_row(["-" * len(column) for column in table.field_names])

            # Обработка правил floating (quick)
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)':
                    if check_rule(rule, ip, num, pf, table, home_pf):
                        filtered_rules.append(rule)
                        num += 1
            # Обработка правил интерфейсов
            for rule in pf.config.filter:
                if rule.floating == 'no':
                    if check_rule(rule, ip, num, pf, table, home_pf):
                        filtered_rules.append(rule)
                        num += 1
            # Обработка правил floating (без quick)
            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '':
                    if check_rule(rule, ip, num, pf, table, home_pf):
                        filtered_rules.append(rule)
                        num += 1

            pf.config.get_html(custom_rules=filtered_rules, save=True, filename=f"report\\{pf.name}.html")

        print(table)
