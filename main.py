from colorama import Fore
from dotenv import load_dotenv
from netaddr import IPAddress, IPNetwork
from prettytable import PrettyTable

from netbox import NetboxAPI
from pfsense import PFSense


def add_rule_to_table(inp_pf, inp_rule, inp_num, inp_table):
    str_source = '\n'.join(
        [f"{Fore.RED if inp_rule.source_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.source_obj['direction']])
    str_destination = '\n'.join(
        [f"{Fore.RED if inp_rule.destination_obj['inverse'] else ''}{j}{Fore.RESET}" for j in
         inp_rule.destination_obj['direction']])
    str_ports = '\n'.join(inp_rule.destination_ports)
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
        inp_rule.descr_full,
        inp_rule.gateway_full,
        str_source,
        str_destination,
        str_ports
    ])


def check_rule(inp_rule, inp_ip, inp_num, inp_pf, inp_table, home):
    # Пропуск отключённых правил
    if rule.disabled != 'no':
        return False

    ### Ищем совпадение в source правила
    find_rule = False
    for source in inp_rule.source_obj['direction']:
        ip_matched = source.ip_in_range(inp_ip)
        if ip_matched and (home or str(source) != '0.0.0.0/0'):
            find_rule = True
    # Если найденный source имеет характеристику NOT ("!") - инвертируем результат поиска
    if inp_rule.source_obj['inverse']:
        find_rule = not find_rule

    ### Если не найдено в source - ищем в destination
    if not find_rule:
        find_rule = False
        for dest in inp_rule.destination_obj['direction']:
            ip_matched = dest.ip_in_range(inp_ip)
            if ip_matched:
                find_rule = True
        # Если найденный destination имеет характеристику NOT ("!") - инвертируем результат поиска
        if inp_rule.destination_obj['inverse']:
            find_rule = not find_rule

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
            ip = input('Enter IP: ')
        except:
            print('\nProgram terminated by user')
            break

        table = PrettyTable(
            ["PF Name", "Num", "Tracker", "Action", "Floating", "Description", "Gateway", "Source", "Destination",
             "Ports"])
        # Включаем показ разделителей между строками таблицы
        table.hrules = 1
        # Ограничение ширины столбца "Description" до 20 символов
        table.max_width["Description"] = 30

        for pf in PFs:
            # if True:
            #     pf = PFs[-1]
            num = 0
            filtered_rules = []

            # Определяем домашний ли pf по отношению к искомому ip
            home_pf = False
            for interface in pf.config.interfaces:
                ip_network_string = interface.get_ip_obj()
                if ip_network_string and IPAddress(ip) in IPNetwork(ip_network_string):
                    home_pf = True
                    break

            table.add_row(["-" * len(column) for column in table.field_names])

            # Обработка правил floating (quick)
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)' and check_rule(rule, ip, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил интерфейсов
            for rule in pf.config.filter:
                if rule.floating == 'no' and check_rule(rule, ip, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1
            # Обработка правил floating (без quick)
            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '' and check_rule(rule, ip, num, pf, table, home_pf):
                    filtered_rules.append(rule)
                    num += 1

            pf.config.get_html(custom_rules=filtered_rules,
                               save=True, filename=f"report\\{pf.name}.html")

        print(table)
