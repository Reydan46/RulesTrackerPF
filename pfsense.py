import datetime
import os
import xml.etree.ElementTree

from log import logger

import paramiko
from netaddr import IPAddress, IPNetwork


class NetPoint:
    network = None
    url = None

    def __init__(self, input_str):
        if not self.parse_ip(input_str):
            if not self.parse_urls(input_str):
                logger.error(f'Error parsing NetPoint: "{input_str}"')

    # noinspection PyBroadException
    def parse_ip(self, input_str):
        try:
            if input_str == 'any':
                self.network = IPNetwork('0.0.0.0/0')
            # Если хотим преобразовывать (self)
            elif input_str == 'interface-(self)':
                self.network = IPNetwork('127.0.0.1/32')
            else:
                self.network = IPNetwork(input_str)
            return True
        except Exception:
            return False

    def parse_urls(self, input_str):
        if input_str:
            # Если хотим игнорировать удалённые интерфейсы
            # and not input_str.startswith('interface-'):
            self.url = input_str
            return True
        return False

    def ip_in_range(self, ip):
        try:
            ip_obj = IPAddress(ip)
            if not self.network:
                return False,None
            if ip_obj not in self.network:
                return False,None
            return True,str(self.network)
        except Exception as e:
            logger.exception(f"Error check IP ({ip}) in range. Error: {e}")
            return False,None

    def __str__(self):
        return str(self.network) if self.network else self.url


class ElementPFSense:
    def __init__(self, xml_tree: xml.etree.ElementTree.Element, elements_str=None, elements_list=None,
                 elements_dict=None, replace=None):
        self.xml_tree = xml_tree

        self.__elements_str = elements_str or {}
        self.__elements_list = elements_list or []
        self.__elements_dict = elements_dict or []
        self.__replace = replace or {}
        self.__replace_def = {'-': '_'}

        for name in self.__elements_str:
            self.__setattr__(name, self.__elements_str[name])
        for name in self.__elements_list:
            self.__setattr__(name, [])
        for name in self.__elements_dict:
            self.__setattr__(name, {})

        self.parse(xml_tree)

    def __eq__(self, other):
        elements_str_match = all(
            self.__getattribute__(name) == other.__getattribute__(name) for name in self.__elements_str)
        elements_list_match = all(
            self.__getattribute__(name) == other.__getattribute__(name) for name in self.__elements_list)
        elements_dict_match = all(
            self.__getattribute__(name) == other.__getattribute__(name) for name in self.__elements_dict)

        return elements_str_match and elements_list_match and elements_dict_match

    def __repr__(self):
        out_str = '\n'
        for key, value in self.__dict__.items():
            if key[0] != '_' and key != 'xml_tree':
                out_str += f'{key:17} : {str(value):15}\n'
        return f'[{out_str}]'

    @staticmethod
    def if_none(text, def_val='') -> str:
        """
        Если значение отсутствует > возвращаем указанное стандартное значение
        В противном случае > возвращаем строковое значение
        """
        return str(text) if text else def_val

    def __replace_tag(self, tag: str):
        for key, value in self.__replace_def.items():
            tag = tag.replace(key, value)
        for key, value in self.__replace.items():
            tag = tag.replace(key, value)
        return tag

    def parse(self, xml_tree: xml.etree.ElementTree.Element):
        element_mappings = {
            'element_str': self.__elements_str,
            'element_list': self.__elements_list,
            'element_dict': self.__elements_dict
        }

        for element in xml_tree.findall('./'):
            elem_name = self.__replace_tag(element.tag)

            if elem_name in element_mappings['element_str']:
                self.__setattr__(elem_name, self.if_none(element.text))

            elif elem_name in element_mappings['element_list']:
                sub_elements = [
                    {
                        'type': sub_elem.tag,
                        'value': self.if_none(sub_elem.text)
                    }
                    for sub_elem in element.findall('./')
                ]
                self.__getattribute__(elem_name).extend(sub_elements)

            elif elem_name in element_mappings['element_dict']:
                sub_elements = {
                    self.__replace_tag(sub_elem.tag): self.if_none(sub_elem.text)
                    for sub_elem in element.findall('./')
                }
                self.__getattribute__(elem_name).update(sub_elements)


class ElementsPFSense:
    def __init__(self, xml_tree: xml.etree.ElementTree.Element,
                 item_class=None, search_name: str = '', filter_tag: str = ''):
        self.xml_tree = xml_tree
        self.elements: list = []

        self.filter_tag = filter_tag if filter_tag else ''
        self.item_class = item_class if item_class else None
        self.search_name = search_name if search_name else ''

        self.parse(xml_tree)

    def __len__(self):
        return self.elements.__len__()

    def __getitem__(self, item):
        if isinstance(item, str):
            return self.__get_element_by_name(item)
        else:
            return self.elements.__getitem__(item)

    def parse(self, xml_tree: xml.etree.ElementTree.Element):
        if self.item_class:
            self.elements = [self.item_class(element) for element in xml_tree.findall(f'./{self.filter_tag}')]

    def __get_element_by_name(self, name: str):
        if self.search_name:
            for element in self.elements:
                if element.__getattribute__(self.search_name) == name:
                    return element


class InterfacePFSense(ElementPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         elements_str={'enable': '', 'ifname': '', 'descr': '', 'ipaddr': '', 'subnet': '',
                                       'gateway': '', 'spoofmac': ''},
                         replace={'if': 'ifname'})
        self.interface: str = xml_tree.tag

    def get_ip_desc(self):
        address = f" ({self.ipaddr}/{self.subnet})" if self.ipaddr and self.subnet else ""
        return f"{self.descr}{address}"

    def get_ip_obj(self):
        return f"{self.ipaddr}/{self.subnet}" if self.ipaddr and self.subnet else ""


class InterfacesPFSense(ElementsPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         item_class=InterfacePFSense,
                         search_name='interface')


class AliasPFSense(ElementPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         elements_str={'name': '', 'type': '', 'address': '', 'descr': '', 'detail': ''})


class AliasesPFSense(ElementsPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         item_class=AliasPFSense,
                         search_name='name')


class RulePFSense(ElementPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         elements_str={'id': '', 'tracker': '-', 'type': 'port forward', 'interface': 'all',
                                       'ipprotocol': '',
                                       'tag': '', 'tagged': '', 'direction': '', 'floating': 'no', 'max': '',
                                       'max_src_nodes': '', 'max_src_conn': '', 'max_src_states': '',
                                       'statetimeout': '', 'statetype': '', 'os': '', 'protocol': 'any', 'descr': '',
                                       'quick': '', 'disabled': 'no', 'state': '', 'gateway': ''},
                         elements_list=['source', 'destination'],
                         elements_dict=['updated', 'created'])

    @staticmethod
    def get_userdate(time_user: dict):
        if 'time' in time_user and 'username' in time_user:
            username = time_user["username"]
            replacements = [' (Local Database)', ' (LDAP/active directory)']
            for replace_str in replacements:
                username = username.replace(replace_str, '')
            formatted_time = datetime.datetime.fromtimestamp(int(time_user['time'])).strftime('%d.%m.%Y %H:%M')
            return f"{formatted_time} by {username}"


class FilterPFSense(ElementsPFSense):
    def __init__(self, xml_tree: xml.etree.ElementTree.Element):
        super().__init__(xml_tree,
                         item_class=RulePFSense,
                         search_name='tracker',
                         filter_tag='rule')


class RulesPFSense:
    def __init__(self, xml_str: str = ''):
        self.interfaces = []
        self.aliases = []
        self.filter = []
        self.search_name = ''
        self.html = ''

        self.xml_tree = xml.etree.ElementTree.fromstring(xml_str)
        for element in self.xml_tree.findall('./'):
            match element.tag:
                case 'interfaces':
                    self.interfaces = InterfacesPFSense(element)
                case 'aliases':
                    self.aliases = AliasesPFSense(element)
                case 'filter':
                    self.filter = FilterPFSense(element)

        self.post_gen_full()
        self.post_gen_obj_search()

    def __len__(self):
        return self.filter.__len__()

    def full_interface(self, interfaces):
        interface_list = interfaces.split(',')
        out_interfaces = [self.interfaces[i].get_ip_desc() if self.interfaces[i] else i for i in interface_list]
        return '<br>'.join(out_interfaces)

    def get_interface(self, interface):
        return self.interfaces[interface].get_ip_desc() if self.interfaces[interface] else interface

    def get_alias(self, alias_name, child_num=0):
        new_line = '&#013;&#010;'
        child_start = '&nbsp;&nbsp;&nbsp;&nbsp;'
        # new_line = '\n'
        # child_start = '\t'

        str_direction = ''
        # Ищем алиас по имени
        alias: AliasesPFSense = self.aliases[alias_name]
        # Если алиас найден
        if alias:
            # Добавляем его название
            str_direction += f"{alias_name}:{new_line}"
            # Пробегаемся по его адресам
            for address in alias.address.split(' '):
                if address == alias.address.split(' ')[-1]:
                    new_line = ''
                str_direction += f"{child_start * child_num}{self.get_alias(address, child_num + 1)}{new_line}"
        else:
            str_direction = alias_name
        return str_direction

    def full_direction(self, direction):
        inverse = False
        address = {}
        port = {}
        for i in direction:
            match i['type']:
                case 'address':
                    address.update({'direction': i['type'], 'value': self.get_alias(i['value'])})
                case 'network':
                    address.update({'direction': i['type'], 'value': self.get_interface(i['value'])})
                case 'any':
                    address.update({'direction': i['type'], 'value': 'any'})
                case 'not':
                    inverse = True
                case 'port':
                    port.update({'direction': i['type'], 'value': self.get_alias(i['value'])})

        # Итоговый словарь
        # {"inverse": inverse, "address": address, "port": port}

        name_address = ''
        value_address = ''
        name_port = ''
        value_port = ''
        if address:
            if address['direction'] == 'address':
                name_address = address['value'].split(':')[0]
                value_address = address['value']
            else:
                name_address = address['value']
        if port:
            if port['direction'] == 'port':
                name_port = port['value'].split(':')[0]
                value_port = port['value']
            else:
                name_port = port['value']

        output = ''
        if inverse:
            output = '<span class="not">NOT </span>'
        if name_address:
            if name_address != value_address and value_address:
                output += f'<span title="{value_address}">{name_address}</span>'
            else:
                output += name_address
        if name_address and name_port:
            output += ' &#8594; '
        if name_port:
            if name_port != value_port and value_port:
                output += f'<span title="{value_port}">{name_port}</span>'
            else:
                output += name_port
        return output

    @staticmethod
    def full_floating(floating, quick):
        return f'{floating} (quick)' if quick else floating

    def post_gen_full(self):
        for rule in self.filter:
            rule.tracker_full = rule.tracker
            rule.gateway_full = rule.gateway
            rule.protocol_full = rule.protocol
            rule.descr_full = rule.descr
            rule.type_full = rule.type
            rule.interface_full = self.full_interface(rule.interface)
            rule.source_full = self.full_direction(rule.source)
            rule.destination_full = self.full_direction(rule.destination)
            rule.floating_full = self.full_floating(rule.floating, rule.quick)
            rule.created_full = rule.get_userdate(rule.created)
            rule.updated_full = rule.get_userdate(rule.updated)

    def get_obj_interface(self, interface):
        out = ''
        if self.interfaces[interface]:
            out = self.interfaces[interface].get_ip_obj()
        return out if out else f'interface-{interface}'

    def get_obj_alias(self, alias_name):
        list_direction = []
        # Ищем алиас по имени
        alias: AliasesPFSense = self.aliases[alias_name]
        # Если алиас найден
        if alias:
            # Пробегаемся по его адресам
            for address in alias.address.split(' '):
                list_direction += self.get_obj_alias(address)
        else:
            list_direction.append(alias_name)
        return list_direction

    def obj_direction(self, direction, rule, path):
        inverse = False
        address = []
        for i in direction:
            match i['type']:
                case 'address':
                    address += self.get_obj_alias(i['value'])
                    if not address[-1]:
                        logger.debug(f'[address] {i['value']}')
                        logger.debug(f'[address] {address[-1]}')
                case 'network':
                    address.append(self.get_obj_interface(i['value']))
                    if not address[-1]:
                        logger.debug(f'[network] {i['value']}')
                        logger.debug(f'[network] {address[-1]}')
                case 'any':
                    if rule.floating == 'no' and rule.interface and path == 'src':
                        address.append(self.get_obj_interface(rule.interface))
                        if not address[-1]:
                            logger.debug(f'[any-interface] {rule.interface}')
                            logger.debug(f'[any-interface] {address[-1]}')
                    else:
                        address.append('0.0.0.0/0')
                case 'not':
                    inverse = True

        output = []

        if address:
            for i in address:
                output.append(NetPoint(i))

        return {'inverse': inverse, 'direction': output}

    def post_gen_obj_search(self):
        for rule in self.filter:
            rule.source_obj = self.obj_direction(rule.source, rule, path='src')
            rule.destination_obj = self.obj_direction(rule.destination, rule, path='dst')


class PFSense:
    def __init__(self, name: str, ip: str, port: int = 22, backup_path: str = '') -> None:
        self.ip: str = ip
        self.port: int = port
        self.backup_path: str = backup_path or os.path.dirname(os.path.abspath(__file__))
        self.config = None
        self.xml_str: str = ''
        self.xml_tree = None
        self.name: str = name

    # Загрузка файла конфигурации в переменную self.xml_str
    def download_config(self):
        logger.info('Trying to download config...')

        # Проверка существования сегодняшнего файла конфигурации локально
        now = datetime.datetime.now()
        save_config_path = os.path.join(self.backup_path, f"configs\\{now.year}\\{now.month:02d}\\{now.day:02d}")
        file_path = os.path.join(save_config_path, f"{self.ip}.xml")
        if os.path.exists(file_path):
            logger.debug(f"Config file {file_path} already exists, loading...")
            with open(file_path, 'r') as file:
                self.xml_str = file.read()
            return True

        # Загрузка файла конфигурации
        try:
            logger.debug(f"Trying to connect to {self.ip}:{self.port}!")
            with paramiko.Transport((self.ip, self.port)) as transport:
                transport.connect(username=os.getenv('PFSENSE_LOGIN'), password=os.getenv('PFSENSE_PASSWORD'))
                with paramiko.SFTPClient.from_transport(transport) as sftp:
                    self.xml_str = sftp.file('/cf/conf/config.xml', 'r').read().decode('UTF-8')

            # Сохранение загруженного файла конфигурации
            logger.debug(f"Config file loaded and saved to {file_path}")
            os.makedirs(save_config_path, exist_ok=True)
            with open(file_path, 'w') as file:
                file.write(self.xml_str)

            return True
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for {self.ip}:{self.port}!")
        except paramiko.SSHException as e:
            logger.error(f"SSH error occurred: {e}")
        except paramiko.sftp.SFTPError as e:
            logger.error(f"SFTP error occurred: {e}")
        except Exception as e:
            logger.exception(f"An error occurred: {e}")

        return False

    def run(self):
        self.download_config()
        if self.xml_str:
            self.config = RulesPFSense(self.xml_str)
