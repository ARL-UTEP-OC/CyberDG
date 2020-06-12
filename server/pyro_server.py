import Pyro4
import os
from pathlib import Path
import vagrant
import threading
import subprocess
import platform

abs_path = Path(__file__).parent.absolute()

@Pyro4.expose
class HostInterface(object):

    def __get_path(self, directory):
        full_path = abs_path
        return full_path / directory

    def _run_command(self, command):
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        return (output, error)

    def get_rdp_ip(self, network):
        command = 'VBoxManage list hostonlyifs'.split()
        result = subprocess.Popen(command, stdout=subprocess.PIPE)
        result = result.stdout
        found = False
        ip = ''
        for line in result:
            if network in line.decode():
                found = True
            if found and 'IPAddress' in line.decode():
                ip = line.split()[1].decode()
                break
        print(ip)
        return ip

    @Pyro4.oneway
    def save_as_base(self, name, vm_name):
        print('Creating Base Image')
        output, error = self._run_command(f'vagrant package --output {vm_name}.box --base {vm_name}')
        if error:
            print('Error: ', error)
        print('Importing Base Image')
        output, error = self._run_command(f'vagrant box add {name} {vm_name}.box')
        if error:
            print('Error: ', error)
        print('Base Image Ready')

    @Pyro4.oneway
    def write_vagrantfile(self, directory, data):
        full_path = self.__get_path(directory)
        Path(full_path).mkdir(parents=True, exist_ok=True)
        file_path = full_path / 'Vagrantfile'
        file = open(file_path, 'w')
        file.write(data)
        file.close()

        full_path_logs = self.__get_path("setup.sh")
        file_path_logs = full_path / 'setup.sh'
        dest = Path(file_path_logs)
        src = Path(full_path_logs)
        dest.write_text(src.read_text())
        os.chdir(Path(__file__).parent.absolute())


    @Pyro4.oneway
    def create_shared_file(self, directory, fname, data):
        full_path = self.__get_path(directory)
        Path(full_path).mkdir(parents=True, exist_ok=True)
        file_path = os.path.join(full_path, fname)
        file = open(file_path, 'w')
        file.write(data)
        file.close()
        os.chdir(Path(__file__).parent.absolute())

    @Pyro4.oneway
    def create_shared_folder(self, directory):
        full_path = self.__get_path(directory)
        Path(full_path).mkdir(parents=True, exist_ok=True)
        os.chdir(Path(__file__).parent.absolute())

    @Pyro4.oneway
    def enable_rdp(self, name, id, port):
        os.system(f'VBoxManage modifyvm {name} --vrde on')
        os.system(f'VBoxManage modifyvm {name} --vrdeport {port}')

    def vagrant_status(self, directory):
        os.chdir(Path(__file__).parent.absolute())
        full_path = self.__get_path(directory)
        vmstatuses = []
        for x in Path(full_path).iterdir():
            if x.is_dir():
                os.chdir(x)
                v = vagrant.Vagrant(quiet_stdout=False, quiet_stderr=False)
                vmstatuses.append(v.status())
        os.chdir(Path(__file__).parent.absolute())
        #print(vmstatuses)
        return vmstatuses


    @Pyro4.oneway
    def vagrant_up(self, directory):
        os.chdir(Path(__file__).parent.absolute())
        full_path = self.__get_path(directory)
        for x in Path(full_path).iterdir():
            if x.is_dir():
                threading.Thread(target=self.__start_vm, args=(x,)).start()
        os.chdir(Path(__file__).parent.absolute())

    @Pyro4.oneway
    def vagrant_halt(self, directory):
        os.chdir(Path(__file__).parent.absolute())
        full_path = self.__get_path(directory)
        for x in Path(full_path).iterdir():
            if x.is_dir():
                threading.Thread(target=self.__stop_vm, args=(x,)).start()
        os.chdir(Path(__file__).parent.absolute())
    
    @Pyro4.oneway
    def vagrant_provision(self, directory):
        os.chdir(Path(__file__).parent.absolute())
        full_path = self.__get_path(directory)
        for x in Path(full_path).iterdir():
            if x.is_dir():
                threading.Thread(target=self.__provision_vm, args=(x,)).start()
        os.chdir(Path(__file__).parent.absolute())

    def ping_pyro_server(self):
        return 200

    def __start_vm(self, directory):
        os.chdir(directory)
        v = vagrant.Vagrant(quiet_stdout=False, quiet_stderr=False)
        v.up()
        v.ssh(command="nohup sudo tshark -i any -q -w /shared/logs/pcaplog.pcapng & sleep 1")
        os.chdir(Path(__file__).parent.absolute())

    def __stop_vm(self, directory):
        os.chdir(directory)
        v = vagrant.Vagrant(quiet_stdout=False, quiet_stderr=False)
        v.halt()

    def __provision_vm(self, directory):
        os.chdir(directory)
        v = vagrant.Vagrant(quiet_stdout=False, quiet_stderr=False)
        v.provision()


def start():
    host = 'localhost'
    if platform.system().lower() == 'windows':
        host = '192.168.99.1'

    Pyro4.Daemon.serveSimple(
        {
            HostInterface: "interface"
        },
        host=host, ns=True, verbose=True)


if __name__ == '__main__':
    start()
