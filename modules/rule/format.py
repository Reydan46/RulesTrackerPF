from colorama import Fore


def format_rule_direction(obj, csv=False):
    if csv:
        return f"{'!' if obj['inverse'] else ''}" + ','.join([f"{j}" for j in obj['direction']]
                                                             )
    return '\n'.join(
        [f"{Fore.RED if obj['inverse'] else ''}{j}{Fore.RESET}" for j in obj['direction']]
    )


def format_rule_interfaces(pf, interfaces, csv=False):
    interface_list = interfaces.split(',')
    if csv:
        return ','.join(
            [pf.config.interfaces[i].descr if pf.config.interfaces[i] else i for i in interface_list]
        )
    return '\n'.join(
        [pf.config.interfaces[i].descr if pf.config.interfaces[i] else i for i in interface_list]
    )


def format_rule_type(rule_type, csv=False):
    if csv:
        return rule_type

    match rule_type:
        case 'block':
            return f"{Fore.RED}BLOCK{Fore.RESET}"
        case 'reject':
            return f"{Fore.RED}REJECT{Fore.RESET}"
        case _:
            return rule_type


def format_rule(inp_pf, inp_rule, inp_num, csv=False):
    str_source = format_rule_direction(inp_rule.source_obj, csv)
    str_destination = format_rule_direction(inp_rule.destination_obj, csv)
    if csv:
        str_ports = ','.join(inp_rule.destination_ports)
    else:
        str_ports = '\n'.join(inp_rule.destination_ports)
    str_interface = format_rule_interfaces(inp_pf, inp_rule.interface, csv)
    str_type = format_rule_type(inp_rule.type, csv)

    return [inp_pf.name,
            f"{inp_num + 1}",
            inp_rule.tracker,
            str_type,
            inp_rule.floating_full,
            inp_rule.protocol_full,
            str_interface,
            str_source,
            str_destination,
            str_ports,
            inp_rule.gateway_full,
            inp_rule.descr_full]
