import Pyro4
from loggers import initialize_logger
from flask import request
import os
from pathlib import Path
from os import path

class VagrantInterface():
    def __init__(self):
        self.logger = initialize_logger()
        self.uri = self.getURI('interface')

    def get_path(self, directory):
        full_path = Path(__file__).parent.absolute()
        return os.path.join(full_path, directory)

    def getURI(self, object_name):
        nameserver = Pyro4.locateNS()
        uri = nameserver.lookup(object_name)
        uri = str(uri).replace('localhost', 'host.docker.internal')
        return uri
    
    def getFileData(self, f):
        basepath = path.dirname(__file__)   
        filepath = path.abspath(path.join(basepath, f.full_path))
        self.logger.info(filepath)
        fl = open(filepath, "r")
        d = fl.read()
        fl.close()
        return d

    def get_rdp_ip(self, network):
        with Pyro4.Proxy(self.uri) as obj:
            ip = obj.get_rdp_ip(network)
            self.logger.info(ip)
            return ip

    def save_as_base(self, name, vm_name):
        with Pyro4.Proxy(self.uri) as obj:
            obj.save_as_base(name, vm_name)

    def write_vagrantfile(self, machine, os, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{machine.scenario_id}/mc_{machine.id}'
            mname = f'{machine.name}-{machine.id}'
            ip = machine.machine_ip
            # Generate vagrantfile

            # Defines the version of Vagrant
            data = 'Vagrant.configure(2) do |config|\n'
            data = f'{data}\tconfig.vm.define \"{mname}\" do |v|\n'
            # Name of the box identified by Virtualbox and Vagrant
            data = f'{data}\t\tv.vm.hostname = \"{mname}\"\n'
            # Select the box to be used for this scenario
            data = f'{data}\t\tv.vm.box = \"{os}\"\n'
            # Network Configurations
            # data = f'{data}\t\tv.vm.network "private_network", ip: \"{ip}\"\n'
            data = f'{data}\t\tv.vm.network "private_network", ip: \"{ip}\"'
            if machine.network_type.name == 'named_network':
                data = f'{data},\n\t\t\tvirtualbox__intnet: \"{machine.network_name}\"\n'
            elif machine.network_type.value == 'Default Internal Network':
                data = f'{data},\n\t\t\tvirtualbox__intnet: \"{scenario.name}{scenario.id}\"\n'
            else:
                data = f'{data}\n'
            if len(machine.file) != 0:
                for f in machine.file:
                    d = self.getFileData(f)
                    obj.create_shared_file(directory + "/shared", f.name, d)
                    data = f'{data}\t\tv.vm.provision "file", source: "shared/{f.name}", destination: "$HOME/shared/"\n'
            else:
                obj.create_shared_folder(directory + "/shared")

            #if machine.cmd_line:
            #    data = f'{data}\t\tv.vm.provision "shell",\n'
            #    data = f'{data}\t\t\tinline: "{machine.cmd_line}"\n'
            data = f'{data}\t\tv.vm.provision :shell, :path => "setup.sh"\n'
            data = f'{data}\t\tconfig.vm.synced_folder "./shared", "/shared"\n'
            # Set Provider to VirtualBox
            data = f'{data}\t\tv.vm.provider "virtualbox" do |vb|\n'
            # Do not display the VirtualBox GUI when booting the machine
            data = f'{data}\t\t\tvb.gui = false\n'
            data = f'{data}\t\t\tvb.name = \"{mname}\"\n'
            # Customize the amount of memory on the VM
            data = f'{data}\t\t\tvb.memory = "{machine.memory}"\n'
            # Customize the cpus
            data = f'{data}\t\t\tvb.cpus = "{machine.processors}"\n'
            # To create host-only rdp ip connection
            with open('../existing_network') as f:
                network = f.readline()
            data = f'{data}\t\t\tv.vm.network "private_network", ip: "10.10.2.2" , :name => "' + network + '", :adapter => 3\n'
            data = f'{data}\t\t\tvb.customize ["modifyvm", :id, "--vrde", "on"]\n'
            data = f'{data}\t\t\tvb.customize ["modifyvm", :id, "--vrdeport", \"{machine.rdp_port}\"]\n'
            # end Virtualbox config
            data = f'{data}\t\tend\n'
            # end vm config
            data = f'{data}\tend\n'
            
            # end vagrantfile
            data = f'{data}end\n'
            
            obj.write_vagrantfile(directory, data)

    def add_inline_commands(self, machine, os, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{machine.scenario_id}/mc_{machine.id}'
            mname = f'{machine.name}-{machine.id}'
            ip = machine.machine_ip
            # Generate vagrantfile

            # Defines the version of Vagrant
            data = 'Vagrant.configure(2) do |config|\n'
            data = f'{data}\tconfig.vm.define \"{mname}\" do |v|\n'
            # Name of the box identified by Virtualbox and Vagrant
            data = f'{data}\t\tv.vm.hostname = \"{mname}\"\n'
            # Select the box to be used for this scenario
            data = f'{data}\t\tv.vm.box = \"{os}\"\n'
            # Network Configurations
            # data = f'{data}\t\tv.vm.network "private_network", ip: \"{ip}\"\n'
            data = f'{data}\t\tv.vm.network "private_network", ip: \"{ip}\"'
            if machine.network_type.name == 'named_network':
                data = f'{data},\n\t\t\tvirtualbox__intnet: \"{machine.network_name}\"\n'
            elif machine.network_type.value == 'Default Internal Network':
                data = f'{data},\n\t\t\tvirtualbox__intnet: \"{scenario.name}{scenario.id}\"\n'
            else:
                data = f'{data}\n'
            if len(machine.file) != 0:
                for f in machine.file:
                    d = self.getFileData(f)
                    obj.create_shared_file(directory + "/shared", f.name, d)
                    data = f'{data}\t\tv.vm.provision "file", source: "shared/{f.name}", destination: "$HOME/shared/"\n'
            else:
                obj.create_shared_folder(directory + "/shared")

            if machine.cmd_line:
                data = f'{data}\t\tv.vm.provision "shell",\n'
                data = f'{data}\t\t\tinline: "{machine.cmd_line}"\n'
            data = f'{data}\t\tconfig.vm.synced_folder "./shared", "/shared"\n'
            # Set Provider to VirtualBox
            data = f'{data}\t\tv.vm.provider "virtualbox" do |vb|\n'
            # Do not display the VirtualBox GUI when booting the machine
            data = f'{data}\t\t\tvb.gui = false\n'
            data = f'{data}\t\t\tvb.name = \"{mname}\"\n'
            # Customize the amount of memory on the VM
            data = f'{data}\t\t\tvb.memory = "{machine.memory}"\n'
            # Customize the cpus
            data = f'{data}\t\t\tvb.cpus = "{machine.processors}"\n'
            # To create host-only rdp ip connection
            with open('../existing_network') as f:
                network = f.readline()
            data = f'{data}\t\t\tv.vm.network "private_network", ip: "10.10.2.2" , :name => "' + network + '", :adapter => 3\n'
            data = f'{data}\t\t\tvb.customize ["modifyvm", :id, "--vrde", "on"]\n'
            data = f'{data}\t\t\tvb.customize ["modifyvm", :id, "--vrdeport", \"{machine.rdp_port}\"]\n'
            # end Virtualbox config
            data = f'{data}\t\tend\n'
            # end vm config
            data = f'{data}\tend\n'
            
            # end vagrantfile
            data = f'{data}end\n'
            
            obj.write_vagrantfile(directory, data)

    def write_ansible_file(self, machine, os):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{machine.scenario_id}/mc_{machine.id}'
            # mname = f'{machine.name}-{machine.id}'
            # ip = machine.machine_ip
            self.logger.info(directory)
            data = ' '
            obj.write_ansible_file(directory, data)

    def enable_rdp(self, machine):
        with Pyro4.Proxy(self.uri) as obj:
            obj.enable_rdp(f'{machine.name}-{machine.id}', f'{machine.id}', f'{machine.rdp_port}')

    def vagrant_up(self, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{scenario.id}'
            self.logger.info(directory)
            obj.vagrant_up(directory)

    def vagrant_halt(self, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{scenario.id}'
            self.logger.info(directory)
            obj.vagrant_halt(directory)

    def vagrant_status(self, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            vmstatuses = []
            directory = f'vagrantfiles/sc_{scenario.id}'
            self.logger.info(directory)
            vmstatuses =  obj.vagrant_status(directory)
            self.logger.info(vmstatuses)
            return vmstatuses
    
    def vagrant_provision(self, scenario):
        with Pyro4.Proxy(self.uri) as obj:
            directory = f'vagrantfiles/sc_{scenario.id}'
            self.logger.info(directory)
            obj.vagrant_provision(directory)

    def ping_pyro_server(self):
        with Pyro4.Proxy(self.uri) as obj:
            result = obj.ping_pyro_server()
            if result == 200:
                return True
