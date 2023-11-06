from modules.rule.format import format_rule
from modules.service.pfsense import RulePFSense, PFSense
from prettytable import PrettyTable


def check_field_match(field, query_field):
    """
    Проверяет совпадение поля с запросом.

    Args:
        field (str): Поле для проверки.
        query_field (dict): Запрос для поля.

    Returns:
        bool: True, если найдено совпадение, в противном случае False.
    """
    if not query_field:
        return True

    value = query_field['value'].lower()
    field_lower = field.lower()

    methods = {
        '+': value in field_lower,
        '=': value == field_lower,
        '!': value != field_lower
    }
    return methods.get(query_field['method'], True)


def check_direction_match(inp_direction, query_field, home=True):
    """
    Проверяет совпадение направления с запросом.

    Args:
        inp_direction (dict): Список объектов направления.
        query_field (dict): Запрос для направления.
        home (bool, optional): Флаг домашней сети. Defaults to True.

    Returns:
        bool: True, если найдено совпадение, в противном случае False.
    """

    def flag_search(item, home, value):
        return home or str(item) != '0.0.0.0/0' or '0.0.0.0' in value

    if not query_field:
        return True

    value = query_field['value']
    direction = inp_direction['direction']
    methods = {
        '+': any(flag_search(item, home, value) and item.ip_in_range(value) for item in direction),
        '=': any(flag_search(item, home, value) and item.ip_exact_match(value) for item in direction),
        '!': all(not (flag_search(item, home, value) and item.ip_in_range(value)) for item in direction)
    }
    found = methods.get(query_field['method'], True)
    if inp_direction['inverse']:
        found = not found
    return found


def check_port_match(destination_ports, port_query):
    """
    Проверяет совпадение порта с запросом.

    Args:
        destination_ports (list): Список целевых портов.
        port_query (dict): Запрос для порта.

    Returns:
        bool: True, если найдено совпадение, в противном случае False.
    """
    if not port_query:
        return True
    value = port_query['value']
    methods = {
        '+': any(value in port for port in destination_ports),
        '=': value in destination_ports,
        '!': value not in destination_ports
    }
    return methods.get(port_query['method'], True)


def check_rule_match(inp_rule, inp_query, inp_num, inp_pf, inp_table, home):
    """
    Проверяет соответствие правила запросу и добавляет его в таблицу, если найдено совпадение.

    Args:
        inp_rule (RulePFSense): Проверяемое правило.
        inp_query (dict): Запрос для правила.
        inp_num (int): Номер входного правила.
        inp_pf (PFSense): Объект PFSense.
        inp_table (PrettyTable): Таблица для добавления совпадающих правил.
        home (bool): Флаг домашней сети.

    Returns:
        bool: True, если найдено совпадение, в противном случае False.
    """
    # Пропуск отключённых правил
    if inp_rule.disabled != 'no':
        return False

    # Проверка pf
    found_pf = check_field_match(inp_pf.name, inp_query['pf'])
    # Проверка action
    found_act = check_field_match(inp_rule.type, inp_query['act'])
    # Проверка description
    found_desc = check_field_match(inp_rule.descr, inp_query['desc'])
    # Проверка source
    found_src = check_direction_match(inp_rule.source_obj, inp_query['src'], home)
    # Проверка destination
    found_dst = check_direction_match(inp_rule.destination_obj, inp_query['dst'])
    # Проверка port
    found_port = check_port_match(inp_rule.destination_ports, inp_query['port'])

    find_rule = all([found_pf, found_act, found_desc, found_src, found_dst, found_port])

    # Если правило подошло под критерии - заносим его в таблицу
    if find_rule:
        inp_table.add_row(format_rule(inp_pf, inp_rule, inp_num))

    return find_rule
