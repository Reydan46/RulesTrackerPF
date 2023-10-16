import ipaddress

import os
from dotenv import load_dotenv

from colorama import Fore
from prettytable import PrettyTable

from netbox import NetboxAPI
from pfsense import PFSense


def print_rule_direction(inp_pf, inp_rule, inp_num, inp_table):
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
        str_ports
    ])


def check_rule(inp_rule, inp_ip, inp_num, inp_pf, inp_table, home):
    flag_find = False
    sub_flag_find = False

    for source in inp_rule.source_obj['direction']:
        ip_matched, network = source.ip_in_range(inp_ip)
        if ip_matched:
            if home:
                sub_flag_find = True
                break
            else:
                if network != '0.0.0.0/0':
                    sub_flag_find = True
                    break

    if inp_rule.source_obj['inverse']:
        sub_flag_find = not sub_flag_find

    if sub_flag_find:
        print_rule_direction(inp_pf, inp_rule, inp_num, inp_table)
        flag_find = True

    if not flag_find:
        sub_flag_find = False

        for dest in inp_rule.destination_obj['direction']:
            ip_matched, network = dest.ip_in_range(inp_ip)
            if ip_matched:
                sub_flag_find = True
                break

        if inp_rule.destination_obj['inverse']:
            sub_flag_find = not sub_flag_find

        if sub_flag_find:
            print_rule_direction(inp_pf, inp_rule, inp_num, inp_table)

    return int(flag_find)


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
    # for router in router_devices:
    if True:
        router = router_devices[0]
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
             "Ports"])
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Description"] = 30

        for pf in PFs:
        # pf = PFs[1]
        # if True:
            separator_row = ["-" * len(column) for column in table.field_names]
            table.add_row(separator_row)
            num = 0
            
            home_pf = False
            interfaces = pf.config.interfaces.elements
            for interface in interfaces:
                if interface.ipaddr and interface.subnet:
                    ip_network_string = f"{interface.ipaddr}/{interface.subnet}"
                    ip_network = ipaddress.IPv4Network(ip_network_string, strict=False)
                    if ipaddress.IPv4Address(ip) in ip_network:
                        home_pf = True
                        break
            
            # ОБработка правил floating (quick)
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)':
                    num += check_rule(rule, ip, num, pf, table, home_pf)

            # Обработка правил интерфейсов
            for rule in pf.config.filter:
                if rule.floating == 'no':
                    num += check_rule(rule, ip, num, pf, table, home_pf)

            # Обработка правил floating (без quick)
            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '':
                    num += check_rule(rule, ip, num, pf, table, home_pf)

        print(table)
