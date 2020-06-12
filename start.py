import argparse
import subprocess
import requests
import time
import sys
sys.path.insert(1, 'app/')
import platform
import shlex
from pathlib import Path


def __run_bash_command(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        print(error)
    return output


def start(args):
    __start_docker(args)
    if not args.docker:
        print('Waiting for Flask Server...')
        __start_pyro_server()
        stop(args)


def __start_docker(args):
    print('Starting Flask Server')
    __correct_env()
    bashCommand = "docker-compose up -d"
    if args.build:
        bashCommand = f'{bashCommand} --build'
        print('Rebuilding Containers')
    __run_bash_command(bashCommand)
    print('Docker is running')


def __start_pyro_server():
    import server.pyro_server as pyro_server
    print('Starting Pyro4 Server')
    pyro_server.start()


def ping_flask_server(args):
    try:
        if platform.system().lower() == 'windows':
            command = 'docker-machine ip'.split()
            result = subprocess.Popen(command, stdout=subprocess.PIPE)
            result = result.stdout.read().decode().strip()
            result = 'http://' + result + ':5000/ping'
            r = requests.get(result)
        else:
            r = requests.get('http://127.0.0.1:5000/ping')
        if r.status_code == 200:
            print('Flask Server is Ready')
        else:
            print('Server not ready')
    except:
        print('Server could not be reached')


def __setup_db():
    try:
        if platform.system().lower() == 'windows':
            command = 'docker-machine ip'.split()
            result = subprocess.Popen(command, stdout=subprocess.PIPE)
            result = result.stdout.read().decode().strip()
            result = 'http://' + result + ':5000/setup_db'
            r = requests.get(result)
        else:
            r = requests.get('http://127.0.0.1:5000/setup_db')
        print("requested setup_db")
        if r.status_code == 200:
            print('Database is Ready')
        else:
            print('Server not ready')
    except Exception as e:
        print(e)
        print('Server could not be reached. Ensure that docker is running and try again.')


def stop(args):
    __run_bash_command("docker-compose down")


def db(args):
    if args.db_operation == 'setup':
        __setup_db()
    elif args.db_operation == 'rebuild':
        __rebuild_db(args)


def __rebuild_db(args):
    print('WARNING: This will delete all data in the database.')
    res = input("Before running this method, all files in app/migrations/versions need to be deleted.  Has this been done? (y/N)\n>")
    if res.lower().strip() != "y" and res.lower().strip() != 'yes':
        print('Please delete all files in app/migrations/versions')
        sys.exit()
    __run_bash_command("docker volume rm practicum_flask_db")
    print('Volume Deleted')
    print('Starting Docker...')
    __start_docker(args)
    time.sleep(5)
    __run_bash_command("docker exec -it flask_app python manage.py db migrate")
    __run_bash_command("docker exec -it flask_app python manage.py db upgrade")
    print("Setting up database")
    __setup_db()
    if not args.up:
        print('Shutting down docker')
        stop(args)
    __check_network()
    print('Rebuild complete')


def check_req(args):
    reqs = ['Pyro4', 'python-vagrant', 'guacapy', 'requests']
    if ('python 2.7' in __run_bash_command('pip --version').decode()):
            output = __run_bash_command('pip3 freeze').decode()
    else:
        output = __run_bash_command('pip freeze').decode()

    for req in reqs:
        if req in output:
            print(f'{req} Installed')
        else:
            print(f'{req} not installed!')

    output = __run_bash_command('docker -v').decode()
    if output.startswith('Docker version'):
        print('Docker Installed')
    else:
        print('Docker not Installed!')

    output = __run_bash_command('vagrant -v').decode()
    if output.startswith('Vagrant'):
        print('Vagrant Installed')
    else:
        print('Vagrant not Installed!')


def __correct_env():
    try:
        env_file = 'debug_mode.env'
        vbox_ip = 'VBOX_IP'
        windows_ip = '192.168.99.1'
        mac_ip = '192.168.33.1'
        new_env = ''
        with open(env_file) as f:
            data = f.readlines()
        for line in data:
            if vbox_ip in line:
                ip = line.split('=')[1]
                if platform.system().lower() == 'windows' and not ip is windows_ip:
                    line = vbox_ip + '=' + windows_ip + '\n'
                if not platform.system().lower() == 'windows' and ip is windows_ip:
                    line = vbox_ip + '=' + mac_ip + '\n'
            new_env = new_env + line
        data = ''.join(data)
        if new_env != data:
            with open(env_file, 'w') as f:
                f.write(new_env)
    except IOError:
        print('Failed to correct debug_mode.env file.')


def __check_network():
    if Path('existing_network').is_file() and not Path('existing_network').stat().st_size == 0:
        with open('existing_network') as f:
            network = f.readline()
        print (network)
        __check_network_settings(network)
    else:
        __create_new()


def __check_network_settings(network):
    command = 'VBoxManage list hostonlyifs'
    output = __run_bash_command(command).decode()
    ip = '10.10.0.1'
    ip_exists = __check_ip_in_use()
    output = output.split(network)
    network_exists = len(output) > 1
    if (network_exists and ip in output[1]):
        print('network set correctly')
    elif (network_exists and ip_exists):
        print('ERROR: Network Does Exist but required Network ip(10.10.0.1) vbox host only adapter in use by other hostonlyifs')
    elif (network_exists and not ip_exists):
        print('network %s not configured correctly needs to be 10.10.0.1/16, configuring now' % network)
        __config_net(network)
    else:
        print('Network %s does not exist, creating new network')
        __create_new()


def __check_ip_in_use():
    command = 'VBoxManage list hostonlyifs'
    output = __run_bash_command(command).decode()
    ip = '10.10.0.1'
    return (ip in output)


def __create_new():
        if __check_ip_in_use():
            print('ERROR: Network ip(10.10.0.1) vbox host only adapter in use by other hostonlyifs')
        network = __make_new()
        __config_net(network)
        with open('existing_network', 'w') as f:
            f.write(network)


def __make_new():
    output = __run_bash_command('VBoxManage hostonlyif create').decode()
    network = output.split("'")[1].strip("'")
    return network


def __config_net(network):
    configure_network = "VBoxManage hostonlyif ipconfig '%s' --ip 10.10.0.1 --netmask 255.255.0.0" % network
    __run_bash_command(configure_network)


def __remove_net():
    with open('existing_network') as f:
        network = f.readline()
    a = "VBoxManage hostonlyif remove '%s'" % network


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage the system')
    subparsers = parser.add_subparsers(help='What operation would you like to take.')

    start_parser = subparsers.add_parser('start', help='Starts the system')
    start_parser.add_argument('--build', help='Rebuilds the docker containers', action='store_true')
    start_parser.add_argument('--docker', help='Starts only Docker without starting the pyro server', action='store_true')
    start_parser.set_defaults(func=start)

    stop_parser = subparsers.add_parser('stop', help='Stops the system')
    stop_parser.set_defaults(func=stop)

    ping_parser = subparsers.add_parser('ping', help='Ping the Flask Server')
    ping_parser.set_defaults(func=ping_flask_server)

    db_parser = subparsers.add_parser('db', help='Basic database operations')
    db_parser.add_argument('db_operation', help='Database operations', choices=['rebuild', 'setup'], default='setup')
    db_parser.add_argument('--build', help='Rebuilds the docker containers after deleting the database volume. Only used during rebuild.', action='store_true')
    db_parser.add_argument('--up', help='Leaves docker running after rebuilding the database. Only used during rebuild.', action='store_true')
    db_parser.set_defaults(func=db)

    req_parser = subparsers.add_parser('check_req', help='Check if the needed requirements are installed')
    req_parser.set_defaults(func=check_req)

    args = parser.parse_args()
    args.func(args)
