import os
import re
from colorama import Fore
from dotenv import load_dotenv
from netaddr import IPAddress, IPNetwork
from prettytable import PrettyTable

from updater import check_update
from netbox import NetboxAPI
from pfsense import PFSense

__github_update_url = 'https://raw.githubusercontent.com/Reydan46/RulesTrackerPF/master/'
__current_version = '1.0'

def parse_search_query(query_string):
    success = True
    fields = ['pf', 'act', 'desc', 'src', 'dst', 'port']
    pattern = re.compile(r'(\w+)([+=!])?=(\S+)')
    query_dict = {field: None for field in fields}

    matches = re.findall(pattern, query_string)
    for match in matches:
        key, method, value = match
        if not method:
            method = '+'
        if key in query_dict:
            query_dict[key] = {'method': method, 'value': value}
        else:
            print(f"{Fore.RED}Invalid key: {key}{Fore.RESET}")
            success = False

    return query_dict, success


def add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table):
    str_source = '\n'.join(
        [f"{Fore.RED if inp_rule.source_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.source_obj['direction']])
    str_destination = '\n'.join(
        [f"{Fore.RED if inp_rule.destination_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.destination_obj['direction']])
    str_ports = '\n'.join(inp_rule.destination_ports)

    interface_list = inp_rule.interface.split(',')
    str_interface = '\n'.join(
        [inp_pf.config.interfaces[i].descr if inp_pf.config.interfaces[i] else i for i in interface_list])
    match inp_rule.type:
        case 'block':
            str_type = f"{Fore.RED}BLOCK{Fore.RESET}"
        case 'reject':
            str_type = f"{Fore.RED}REJECT{Fore.RESET}"
        case _:
            str_type = inp_rule.type
    inp_table.add_row([
        inp_pf.name,
        f"{inp_num + 1}",
        inp_rule.tracker,
        str_type,
        inp_rule.floating_full,
        str_interface,
        str_source,
        str_destination,
        str_ports,
        inp_rule.gateway_full,
        inp_rule.descr_full,
    ])


def check_rule(inp_rule, inp_query, inp_num, inp_pf, inp_table, home):
    def check_field(field, query_field):
        found = True
        if query_field:
            match query_field['method']:
                case '+':
                    found = False
                    if query_field['value'].lower() in field.lower():
                        found = True
                case '=':
                    found = query_field['value'].lower() == field.lower()
                case '!':
                    found = query_field['value'].lower() != field.lower()
        return found

    # Пропуск отключённых правил
    if rule.disabled != 'no':
        return False

    # Проверка pf
    found_pf = check_field(pf.name, inp_query['pf'])
    # Проверка action
    found_act = check_field(rule.type, inp_query['act'])
    # Проверка description
    found_desc = check_field(rule.descr, inp_query['desc'])

    found_src = True
    if inp_query['src']:
        # Ищем совпадение в source правила
        found_src = False
        for source in inp_rule.source_obj['direction']:
            ip_matched = source.ip_in_range(inp_query['src']['value'])
            if ip_matched and (home or str(source) != '0.0.0.0/0'):
                found_src = True
        # Если найденный source имеет характеристику NOT ("!") - инвертируем результат поиска
        if inp_rule.source_obj['inverse']:
            found_src = not found_src

    found_dst = True
    if inp_query['dst']:
        # Ищем совпадение в destination правила
        found_dst = False
        for dest in inp_rule.destination_obj['direction']:
            ip_matched = dest.ip_in_range(inp_query['dst']['value'])
            if ip_matched:
                found_dst = True
        # Если найденный destination имеет характеристику NOT ("!") - инвертируем результат поиска
        if inp_rule.destination_obj['inverse']:
            found_dst = not found_dst

    found_port = True
    if inp_query['port']:
        match inp_query['port']['method']:
            case '+':
                found_port = False
                for port in inp_rule.destination_ports:
                    if inp_query['port']['value'] in port:
                        found_port = True
                        break
            case '=':
                found_port = inp_query['port']['value'] in inp_rule.destination_ports
            case '!':
                found_port = inp_query['port']['value'] not in inp_rule.destination_ports

    find_rule = found_pf and found_act and found_desc and found_src and found_dst and found_port

    # Если поиск правила был успешен - заносим его в таблицу
    if find_rule:
        add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table)

    return find_rule


if __name__ == '__main__':
    check_update(__github_update_url, __current_version)

    router_devices = []

    # Загрузка переменных окружения из .env
    load_dotenv(dotenv_path='.env')
    # Создание подключения с NetBox
    if NetboxAPI.create_connection():
        # Получение ролей устройств с NetBox
        if NetboxAPI.get_roles() and 'Router' in NetboxAPI.roles:
            # Получение устройств с ролью router (в нашем случае это все pfSense)
            router_devices = NetboxAPI.get_devices(
                role=NetboxAPI.roles['Router'])

    PFs = []
    # if True:
    #     router = router_devices[1]
    for router in router_devices:
        pf = PFSense(
            ip=router.primary_ip4.address.split('/')[0],
            name=router.name
        )
        pf.run()
        PFs.append(pf)

    # Search Console
    while True:
        try:
            query = input('Enter query: ')
            parsed_query, parsed_success = parse_search_query(query)

            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            print('\nProgram terminated by user')
            break
        if not parsed_success:
            input('Press Enter to continue...')
            continue

        table = PrettyTable(
            ["PF Name", "Num", "Tracker", "Action", "Floating", "Interface", "Source", "Destination", "Ports",
             "Gateway", "Description"])
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Action"] = 7
        table.max_width["Description"] = 30
        table.max_width["Source"] = 20
        table.max_width["Destination"] = 20

        for pf in PFs:
            # if True:
            #     pf = PFs[-1]
            num = 0
            filtered_rules = []

            # Определяем домашний ли pf по отношению к искомому ip
            if parsed_query['src']:
                home_pf = False
                for interface in pf.config.interfaces:
                    ip_network_string = interface.get_ip_obj()
                    if ip_network_string and IPAddress(parsed_query['src']['value']) in IPNetwork(ip_network_string):
                        home_pf = True
                        break
            else:
                # Если source не указан - считаем домашними все PFSense
                home_pf = True

            # Обработка правил floating (quick)
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)' and check_rule(rule, parsed_query, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил интерфейсов
            for rule in pf.config.filter:
                if rule.floating == 'no' and check_rule(rule, parsed_query, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил floating (без quick)
            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '' and check_rule(rule, parsed_query, num, pf, table,
                                                                              home_pf):
                    filtered_rules.append(rule)
                    num += 1

            pf.config.get_html(custom_rules=filtered_rules,
                               save=True, filename=f"report\\{pf.name}.html")

            if filtered_rules and pf != PFs[-1]:
                table.add_row(["-" * len(column) for column in table.field_names])

        print(table)
