from dotenv import load_dotenv

from netbox import NetboxAPI
from pfsense import PFSense

from prettytable import PrettyTable
from colorama import Fore


def print_rule_direction(inp_pf, inp_rule, inp_num, inp_table):
    source_inverse = True if inp_rule.source_obj['inverse'] else False
    str_source = '\n'.join(
        [f"{Fore.RED if source_inverse else ''}{j}{Fore.RESET}" for j in inp_rule.source_obj['direction']])
    destination_inverse = True if inp_rule.destination_obj['inverse'] else False
    str_destination = '\n'.join(
        [f"{Fore.RED if destination_inverse else ''}{j}{Fore.RESET}" for j in inp_rule.destination_obj['direction']])
    str_floating = inp_rule.floating_full
    str_ports = ''
    for cnf in inp_rule.destination:
        if cnf['type'] == 'port':
            str_ports = cnf['value']
    str_type = inp_rule.type

    inp_table.add_row([
        inp_pf.name,
        str(inp_num + 1),
        inp_rule.tracker,
        str_type,
        str_floating,
        inp_rule.descr_full,
        inp_rule.gateway_full,
        str_source,
        str_destination,
        str_ports
    ])


def check_rule(inp_rule, inp_ip, inp_num, inp_pf, inp_table):
    flag_find = False
    sub_flag_find = False

    for source in inp_rule.source_obj['direction']:
        if source.ip_in_range(inp_ip):
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
            if dest.ip_in_range(inp_ip):
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
    for router in router_devices:
        pf = PFSense(
            ip=router.primary_ip4.address.split('/')[0],
            name=router.name
        )
        pf.run()
        PFs.append(pf)

    # Search Console
    while True:
        ip = input('Enter IP: ')
        table = PrettyTable(
            ["PF Name", "Num", "Tracker", "Action", "Floating", "Description", "Gateway", "Source", "Destination",
             "Ports"])
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Description"] = 30

        for pf in PFs:
            # pf = PFs[0]
            # if True:
            separator_row = ["-" * len(column) for column in table.field_names]
            table.add_row(separator_row)
            num = 0
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)':
                    num += check_rule(rule, ip, num, pf, table)

            for rule in pf.config.filter:
                if rule.floating == 'no':
                    num += check_rule(rule, ip, num, pf, table)

            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '':
                    num += check_rule(rule, ip, num, pf, table)

        print(table)
