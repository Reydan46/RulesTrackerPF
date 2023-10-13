import os
import datetime
import pickle

import pynetbox
import pynetbox.core.response

from log import logger


class NetboxAPI:
    __netbox_connection = None
    roles = None

    # Создание соединения c NetBox
    @classmethod
    def create_connection(cls):
        try:
            logger.debug("Trying to connect to NetBox")
            cls.__netbox_connection = pynetbox.api(
                url=os.getenv('NETBOX_URL'),
                token=os.getenv('NETBOX_TOKEN')
            )
            logger.debug("Connection to NetBox established")
            return True
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            return False

    # @classmethod
    # def get_roles(cls):
    #     logger.debug("Getting roles from NetBox")
    #     cls.roles = {
    #         role.name: role for role in cls.__netbox_connection.dcim.device_roles.all()
    #     }

    @classmethod
    def get_roles(cls):
        cache_file = "roles_cache.pkl"
        cache_expiry = datetime.timedelta(hours=1)

        if os.path.exists(cache_file):
            with open(cache_file, "rb") as file:
                cache_data = pickle.load(file)
                if (
                        cache_data is not None
                        and "roles" in cache_data
                        and "timestamp" in cache_data
                        and isinstance(cache_data["timestamp"], datetime.datetime)
                        and datetime.datetime.now() - cache_data["timestamp"] <= cache_expiry
                ):
                    cls.roles = cache_data["roles"]
                    return

        logger.debug("Getting roles from NetBox")
        roles = {
            role.name: role for role in cls.__netbox_connection.dcim.device_roles.all()
        }

        cache_data = {"roles": roles, "timestamp": datetime.datetime.now()}
        with open(cache_file, "wb") as file:
            pickle.dump(cache_data, file)

        cls.roles = roles

    @classmethod
    def get_devices(cls, role: pynetbox.core.response.Record):
        logger.debug(f"Getting devices with role '{role}' from NetBox")
        try:
            devices = cls.__netbox_connection.virtualization.virtual_machines.filter(role_id=role.id)
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            devices = None

        return devices

    @classmethod
    def get_interfaces(cls, virtual_machine):
        return cls.__netbox_connection.virtualization.interfaces.filter(
            virtual_machine=virtual_machine.name
        )
