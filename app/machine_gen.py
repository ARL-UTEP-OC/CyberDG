from models import Machine, Config, OS


def generate(scenario, machine, rec_os, packages=None):
    rec_ip = generate_ip(scenario.id, machine.id)
    rec_port = generate_port(machine.id)


    machine.machine_ip = rec_ip
    machine.rdp_port = rec_port
    machine.os_id = (OS.query.filter_by(name=rec_os).first()).id
    return machine


# this ip is only for vagrant file not guac server
def generate_ip(scen_no, mach_no):
    return '10.10.'+str(scen_no+1)+'.'+str(mach_no+1)


# port will only support up to 999 scenarios
def generate_port(mach_no):
    if(mach_no < 1000):
        return (5000+mach_no)
    else:
        return mach_no
