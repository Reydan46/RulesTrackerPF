from dotenv import load_dotenv

from netbox import NetboxAPI
from pfsense import PFSense


def print_rule_direction(inp_pf, inp_rule, inp_num):
    str_source_inverse = "!" if inp_rule.source_obj['inverse'] else ""
    str_source = ', '.join([str(j) for j in inp_rule.source_obj['direction']])
    str_destination_inverse = "!" if inp_rule.destination_obj['inverse'] else ""
    str_destination = ', '.join([str(j) for j in inp_rule.destination_obj['direction']])
    str_floating = inp_rule.floating_full
    str_ports = ''
    for cnf in inp_rule.destination:
        if cnf['type'] == 'port':
            str_ports = f'[{cnf['value']}]'
    str_type = inp_rule.type
    print(f'[{inp_pf.name:7}][{str(inp_num).center(4)}][{inp_rule.tracker}][{str_type}][{str_floating.center(11)}] '
          f'"{inp_rule.descr_full.center(40)}" '
          f'{str_source_inverse}{f'({str_source})'.center(20)}'
          f' > '
          f'{str_destination_inverse}({str_destination}){str_ports}')


def check_rule(inp_rule, inp_ip, inp_num, inp_pf):
    flag_find = False
    sub_flag_find = False

    for source in inp_rule.source_obj['direction']:
        if source.ip_in_range(inp_ip):
            sub_flag_find = True
            break

    if inp_rule.source_obj['inverse']:
        sub_flag_find = not sub_flag_find

    if sub_flag_find:
        inp_num += 1
        print_rule_direction(inp_pf, inp_rule, inp_num)
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
            inp_num += 1
            print_rule_direction(inp_pf, inp_rule, inp_num)

    return inp_num


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
                    num = check_rule(rule, ip, num, pf)

            for rule in pf.config.filter:
                if rule.floating == 'no':
                    num = check_rule(rule, ip, num, pf)

            for rule in pf.config.filter:
                if rule.floating == 'yes' and rule.quick == '':
                    num = check_rule(rule, ip, num, pf)

        print("#" * 20)
