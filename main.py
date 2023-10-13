from dotenv import load_dotenv

from log import logger
from netbox import NetboxAPI
from pfsense import PFSense

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
        # for pf in PFs:
        pf = PFs[0]
        if True:
            print("#" * 20)
            num = 0
            for rule in pf.config.filter:
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
                        str_source_inverse = "!" if rule.source_obj['inverse'] else ""
                        str_source = ', '.join([str(j) for j in rule.source_obj['direction']])
                        str_destination_inverse = "!" if rule.destination_obj['inverse'] else ""
                        str_destination = ', '.join([str(j) for j in rule.destination_obj['direction']])
                        print(f'[{pf.name:7}][{num:4}][src][{rule.tracker}] '
                              f'"{rule.descr_full:33}" '
                              f'{str_source_inverse}({str_source}) > {str_destination_inverse}({str_destination})')
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
                        str_source_inverse = "!" if rule.source_obj['inverse'] else ""
                        str_source = ', '.join([str(j) for j in rule.source_obj['direction']])
                        str_destination_inverse = "!" if rule.destination_obj['inverse'] else ""
                        str_destination = ', '.join([str(j) for j in rule.destination_obj['direction']])
                        print(f'[{pf.name:7}][{num:4}][dst][{rule.tracker}] '
                              f'"{rule.descr_full:33}" '
                              f'{str_source_inverse}({str_source}) > {str_destination_inverse}({str_destination})')
                        flag_find = True

        print("#" * 20)
