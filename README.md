# Cybersecurity Dataset Generator

### First Time Start

1. Install Docker: https://www.docker.com/products/docker-desktop
    Docker Toolbox for Windows

1. Install Vagrant: https://www.vagrantup.com/downloads.html
    Follow the advice found in these sections before continuing
        #### ERROR: for nameserver  Cannot start service nameserver: network <hash> not found
        #### On Windows File doesnt exist, error on vagrantinterface

1. Install Pyro4: `pip install Pyro4`

1. Install python-vagrant: `pip install python-vagrant`

1. Install requests: `pip install requests`

1. Install requests: `pip install guacapy`

2. Clone repo

3. Navigate to repo folder (where the `start.py` file is)

3. Verify everything is installed: `python start.py check_req`.  If anything is not installed, install it before continuing.

4. Build the system: `python start.py db rebuild`

    Note: This will take some time to complete

5. Start the system: `python start.py start`

6. Navigate to `http://0.0.0.0:5000/`

7. Shutdown the system: `ctrl-c`


### Subsequent Starts

1. Navigate to the project folder and start the system: `python start.py start`

2. In a web browser, navigate to `http://0.0.0.0:5000/`

3. To stop the server: `ctrl-c`

### Troubleshooting

#### ERROR: for nameserver  Cannot start service nameserver: network <hash> not found
If on windows and using DockerToolbox, add the following port forwading rule to the default vm by using virtualbox, do not remove existing rules:
    Name            Protocol        Host IP         Host Port       Guest Port
    nameserver      TCP             127.0.0.1       9090            9090
    guac_rdp        TCP             127.0.0.1       8080            8080


#### Site can't be reached (localhost refused connection) (Windows OS)
If all of the containers are running (none of them exited) but no site is being served to `http://0.0.0.0:5000/`, you may need to navigate to Docker's IP address instead of localhost. To obtain Docker's IP, run `docker machine ip`. Then navigate to port 5000 of that IP

#### sqlalchemy.exc.ProgrammingError
The `models.py` file is not in sync with the database.  The database needs to be brought up to speed with the `models.py`.

1. Delete everything in the `app/migrations/versions` folder

1. Rebuild the database: `python start.py db rebuild`

2. Start the system: `python start.py start`

#### On Windows File doesnt exist, error on vagrantinterface
1. add virtualbox folder to path:
    'C:\Program Files\Oracle\VirtualBox\'

#### ERROR: Network Does Exist but required Network ip(10.10.0.1) vbox host only adapter in use by other hostonlyifs
1. If you want to repurpose the existing hostonly adapter, in the same directory open or create the file "existing_network" and put the name of the corresponding network inside:
        Examples of file:
            Windows: "VirtualBox Host-Only Ethernet Adapter #2"
            Mac: "vboxnet1"
