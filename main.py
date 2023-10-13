from dotenv import load_dotenv

from log import logger
from netbox import NetboxAPI
from pfsense import PFSense


def print_rule_direction(pf, rule, num):
    str_source_inverse = "!" if rule.source_obj['inverse'] else ""
    str_source = ', '.join([str(j) for j in rule.source_obj['direction']])
    str_destination_inverse = "!" if rule.destination_obj['inverse'] else ""
    str_destination = ', '.join([str(j) for j in rule.destination_obj['direction']])
    str_floating = rule.floating_full
    str_ports = ''
    for cnf in rule.destination:
        if cnf['type'] == 'port':
            str_ports = f'[{cnf['value']}]'
    str_type = rule.type
    print(f'[{pf.name:7}][{str(num).center(4)}][{rule.tracker}][{str_type}][{str_floating.center(11)}] '
          f'"{rule.descr_full.center(40)}" '
          f'{str_source_inverse}{f'({str_source})'.center(20)} > {str_destination_inverse}({str_destination}){str_ports}')

def check_rule(rule, ip, num, pf):
    flag_find = False
    if not flag_find:
        sub_flag_find = False

        for source in rule.source_obj['direction']:
            if source.ip_in_range(ip):
                sub_flag_find = True
                break

        if rule.source_obj['inverse']:
            sub_flag_find = not sub_flag_find

        if sub_flag_find:
            num += 1
            print_rule_direction(pf, rule, num)
            flag_find = True

    if not flag_find:
        sub_flag_find = False

        for dest in rule.destination_obj['direction']:
            if dest.ip_in_range(ip):
                sub_flag_find = True
                break

        if rule.destination_obj['inverse']:
            sub_flag_find = not sub_flag_find

        if sub_flag_find:
            num += 1
            print_rule_direction(pf, rule, num)
            flag_find = True

if __name__ == '__main__':
    # Загрузка переменных окружения из .env
    load_dotenv()
    # Создание подключения с NetBox
    NetboxAPI.create_connection()
    # Получение ролей устройств с NetBox
    NetboxAPI.get_roles()
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

    # Search BAD
    while True:
        ip = input('Enter IP:')
        for pf in PFs:
            # pf = PFs[0]
            # if True:
            print("#" * 20)
            num = 0
            for rule in pf.config.filter:
                if rule.floating_full == 'yes (quick)':
                    check_rule(rule, ip, num, pf)

            for rule in pf.config.filter:
                if rule.floating == 'no':
                    check_rule(rule, ip, num, pf)

            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '':
                    check_rule(rule, ip, num, pf)

        print("#" * 20)
