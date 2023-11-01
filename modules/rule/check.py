from modules.rule.format import format_rule


def check_field(field, query_field):
    is_found = True

    if not query_field:
        return is_found

    match query_field['method']:
        case '+':
            is_found = query_field['value'].lower() in field.lower()
        case '=':
            is_found = query_field['value'].lower() == field.lower()
        case '!':
            is_found = query_field['value'].lower() != field.lower()
    return is_found


def check_rule(inp_rule, inp_query, inp_num, inp_pf, inp_table, home):
    # Пропуск отключённых правил
    if inp_rule.disabled != 'no':
        return False

    # Проверка pf
    found_pf = check_field(inp_pf.name, inp_query['pf'])
    # Проверка action
    found_act = check_field(inp_rule.type, inp_query['act'])
    # Проверка description
    found_desc = check_field(inp_rule.descr, inp_query['desc'])

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
                found = [inp_query['port']['value'] in port for port in inp_rule.destination_ports]
                found_port = True if not found else any(found)
            case '=':
                found_port = inp_query['port']['value'] in inp_rule.destination_ports
            case '!':
                found_port = inp_query['port']['value'] not in inp_rule.destination_ports

    find_rule = found_pf and found_act and found_desc and found_src and found_dst and found_port

    # Если правило подошло под критерии - заносим его в таблицу
    if find_rule:
        inp_table.add_row(format_rule(inp_pf, inp_rule, inp_num))

    return find_rule
