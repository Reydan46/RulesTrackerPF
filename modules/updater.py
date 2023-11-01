import requests
import sys
import os
from modules.log import logger


def check_update(github_update_url, current_version):
    try:
        response = requests.get(github_update_url + 'version')
        response.raise_for_status()

        latest_version = response.text.strip()

        if latest_version != current_version:
            logger.info(f"Updating to version {latest_version}")
            update_files(latest_version, github_update_url)
        else:
            logger.info("Running the latest version.")

    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")


def update_files(updated_version, github_update_url):
    try:
        response = requests.get(github_update_url + 'file_list')
        response.raise_for_status()
        files = [i for i in response.text.split('\n') if i]

        for file in files:
            file_path = os.path.join(*file.split('/'))
            directory = os.path.dirname(file_path)

            try:
                if directory:
                    os.makedirs(directory, exist_ok=True)
                logger.info(f"Downloading: {github_update_url}{file}")
                response = requests.get(github_update_url + file)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                logger.warning(f"No write access to the directory: {directory}. Error: {e}")

        logger.info(f"Exiting from script. Restart manual with version {updated_version}")
        sys.exit(0)
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
