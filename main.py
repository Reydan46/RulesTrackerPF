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
        for pf in PFs:
            print("#" * 20)
            num = 0
            for rule in pf.config.filter:
                flag_find = False
                if not flag_find:
                    for source in rule.source_obj:
                        if source.ip_in_range(ip):
                            num += 1
                            print(f'[{pf.name:7}][{num:4}][src][{rule.tracker}] '
                                  f'"{rule.descr_full:33}" '
                                  f'({', '.join([str(j) for j in rule.source_obj])}) > ({', '.join([str(j) for j in rule.destination_obj])})')
                            flag_find = True
                            break
                if not flag_find:
                    for dest in rule.destination_obj:
                        if dest.ip_in_range(ip):
                            num += 1
                            print(f'[{pf.name:7}][{num:4}][dst][{rule.tracker}] '
                                  f'"{rule.descr_full:33}" '
                                  f'({', '.join([str(j) for j in rule.source_obj])}) > ({', '.join([str(j) for j in rule.destination_obj])})')
                            break
        print("#" * 20)
