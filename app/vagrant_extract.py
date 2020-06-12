

class VagrantExtract():

    def __init__(self, vgfile):
        self.vgfile = vgfile

    def parse_for_db(self):
        vg = open(self.vgfile, "r+")
        vmlist = {}
        vmname = ""
        for line in vg:
            # Counting how many vms are in the file
            if 'vm.define' in line and '#' not in line:
                tmp = line.split()
                #vmnames.append(tmp[1].strip('\"'))
                vmname = tmp[1].strip('\"')
                vmlist[vmname] = {}
            if 'vm.box' in line and '#' not in line:
                tmp = line.split()
                vmlist[vmname]['os'] = tmp[2].strip('\"')

            if 'vm.network' in line and '#' not in line:
                tmp = line.split()
                vmlist[vmname]['ip'] = tmp[3].strip('\"')

        print(vmlist)
        vg.close()
        return vmlist
