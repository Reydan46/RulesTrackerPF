# Purpose
Script to connect PFSense rule filtering by specified search criteria.

# Settings .env
| Value            | Description                | Example                                  |
|------------------|----------------------------|------------------------------------------|
| PFSENSE_LOGIN    | pfSense user name          | sftp-user                                |
| PFSENSE_PASSWORD | PfSense user password      | P@ssw0rd                                 |
| NETBOX_URL       | NetBox server URL          | http://netbox:8080                       |
| NETBOX_TOKEN     | Token to connect to NetBox | 11d41abff2560c1cd7835a294c8284dfcaa62c72 |


# Notes
1. You need to add all instances of pfSense servers to the NetBox with the 'router' role
2. Оn the pfSense servers you need to create a user with SFTP connection rights and read-only access to the configuration file.
3. After the first run, a settings.yaml file will be created containing the caching time of the data received from NetBox and pfSense

# Install
1. Install Python 3.10 (or higher)
2. Download and unzip the [Install.zip](https://github.com/Reydan46/RulesTrackerPF/releases/download/Install/Install.zip) file
3. Generate a token from NetBox
    * Go to the netbox website
    * In the upper right corner click on your username
    * API Tokens.
    * Add token > Create
    * Copy the token to the .env file (NETBOX_TOKEN).
4. Start the installation
    * Linux:
      * chmod +x start.sh
      * ./start.sh
    * Windows:
      * Right-click on the file start.ps1
      * Run with PowerShell
5. After installation, re-run the start script

# Forming a search request
### Possible search fields
| Field | Description                        | Example search |
|-------|------------------------------------|----------------|
| pf    | Name of pfSense server from NetBox | pf=srv-pf      |
| act   | Rule Field  Action                 | act=pass       |
| desc  | Rule Field  Description            | desc=test      |
| src   | Rule Field  Source                 | src=10.10.10.1 | 
| dst   | Rule Field  Destination            | dst=10.10.10.1 |
| port  | Rule Field  Destination Port       | port=22        |
### Possible search types
| Type | Description | Example search | What will be found |
|------|-------------|----------------|--------------------|
| +=   | Incoming    | port=22        | any, 22, 5222      |
| =    | Same as =   | port=22        | any, 22, 5222      |
| ==   | Match       | port=22        | 22                 |
| !=   | Exception   | port=22        | any, 5222          |
