import os

import pynetbox
import pynetbox.core.response

from modules.cache import cache_get, cache_set
from modules.log import logger


class NetboxAPI:
    __netbox_connection = None
    roles = None
    settings = None

    # Создание соединения c NetBox
    @classmethod
    def create_connection(cls):
        try:
            logger.debug("Trying to connect to NetBox")
            url = os.getenv('NETBOX_URL')
            token = os.getenv('NETBOX_TOKEN')
            if not url:
                logger.error("NetBox URL is not set")
                return False
            if not token:
                logger.error("NetBox token is not set")
                return False
            cls.__netbox_connection = pynetbox.api(
                url=url,
                token=token
            )
            logger.debug("Connection to NetBox established")
            return True
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            return False

    @classmethod
    def get_roles(cls):
        logger.debug("Checking cache for roles")
        cls.roles = {}
        cache_file = "netbox_roles.pkl"

        cache_data = cache_get(
            cache_file,
            days=cls.settings['cache']['netbox']['roles']['days'],
            hours=cls.settings['cache']['netbox']['roles']['hours'],
            minutes=cls.settings['cache']['netbox']['roles']['minutes']
        )
        if cache_data is not None:
            logger.debug("Roles loaded from cache")
            cls.roles = cache_data
            return True

        logger.debug("Getting roles from NetBox")
        try:
            roles = {
                role.name: role for role in cls.__netbox_connection.dcim.device_roles.all()
            }
            logger.debug("Roles retrieved from NetBox API")
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            cls.roles = {}
            return False

        cache_set(roles, cache_file)
        cls.roles = roles
        return True

    @classmethod
    def get_devices(cls, role: pynetbox.core.response.Record):
        logger.debug("Checking cache for devices")
        devices = []
        cache_file = "netbox_devices.pkl"

        cache_data = cache_get(
            cache_file,
            days=cls.settings['cache']['netbox']['devices']['days'],
            hours=cls.settings['cache']['netbox']['devices']['hours'],
            minutes=cls.settings['cache']['netbox']['devices']['minutes']
        )
        if cache_data is not None:
            logger.debug("Devices loaded from cache")
            return cache_data

        logger.debug("Getting devices from NetBox")
        try:
            devices_generator = cls.__netbox_connection.virtualization.virtual_machines.filter(
                role_id=role.id
            )
            devices = list(devices_generator)
            logger.debug("Devices retrieved from NetBox API")
        except Exception as e:
            logger.exception(f"An error occurred: {e}")

        cache_set(devices, cache_file)
        return devices

    @classmethod
    def get_interfaces(cls, virtual_machine):
        return cls.__netbox_connection.virtualization.interfaces.filter(
            virtual_machine=virtual_machine.name
        )

    @classmethod
    def get_ip_addresses(cls, virtual_machine):
        return cls.__netbox_connection.ipam.ip_addresses.filter(
            virtual_machine=virtual_machine.name
        )
