import re
from colorama import Fore
from dotenv import load_dotenv
from netaddr import IPAddress, IPNetwork
from prettytable import PrettyTable

from netbox import NetboxAPI
from pfsense import PFSense


def parse_search_query(query_string):
    fields = ['pf', 'act', 'desc', 'src', 'dst', 'port']
    pattern = re.compile(r'(\w+)=(\S+)')
    query_dict = {field: None for field in fields}

    matches = re.findall(pattern, query_string)
    for match in matches:
        key, value = match
        if key in query_dict:
            query_dict[key] = value

    return query_dict


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
    # Пропуск отключённых правил
    if rule.disabled != 'no':
        return False

    # Проверка pf
    found_pf = True
    if inp_query['pf']:
        found_pf = False
        if inp_query['pf'].lower() in inp_pf.name.lower():
            found_pf = True

    # Проверка action
    found_act = True
    if inp_query['act']:
        found_act = False
        if inp_query['act'].lower() in rule.type.lower():
            found_act = True

    # Проверка description
    found_desc = True
    if inp_query['desc']:
        found_desc = False
        if inp_query['desc'].lower() in rule.descr.lower():
            found_desc = True

    found_src = True
    if inp_query['src']:
        # Ищем совпадение в source правила
        found_src = False
        for source in inp_rule.source_obj['direction']:
            ip_matched = source.ip_in_range(inp_query['src'])
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
            ip_matched = dest.ip_in_range(inp_query['dst'])
            if ip_matched:
                found_dst = True
        # Если найденный destination имеет характеристику NOT ("!") - инвертируем результат поиска
        if inp_rule.destination_obj['inverse']:
            found_dst = not found_dst

    found_port = True
    if inp_query['port']:
        found_port = False
        for port in inp_rule.destination_ports:
            if inp_query['port'] in port:
                found_port = True
                break

    find_rule = found_pf and found_act and found_desc and found_src and found_dst and found_port

    # Если поиск правила был успешен - заносим его в таблицу
    if find_rule:
        add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table)

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
            parsed_query = parse_search_query(query)
        except:
            print('\nProgram terminated by user')
            break

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
                    if ip_network_string and IPAddress(parsed_query['src']) in IPNetwork(ip_network_string):
                        home_pf = True
                        break
            else:
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
