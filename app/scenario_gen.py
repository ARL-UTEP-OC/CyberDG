from models import (db, GuacUser, Scenario, Machine, Config, OS)
import machine_gen
from shutil import copyfile

default_os = 'Kali'
name = ""
mach_no=1

# ID OS based on file template "tested on:    Higher accuracy"
def find_test_os(x_file):
    print("--READING FILE SPECIFICATIONS --\n")
    ef = open(x_file.full_path, 'r')
    exploit_file = ef.read()
    lines = exploit_file.split()
    tested = "tested"
    for line in lines:
        if tested in line.lower() and "version" not in line.lower():
            return id_recommendations(line)
    # if we get to this part file did not have keyword, so we guess
    ef.close()
    return guess_test_os(x_file)


# ID OS based on finding keywords throughout document  Lower acccuracy"
def guess_test_os(x_file):
    print("--GUESSING--\n")
    f = open(x_file.full_path, 'r')
    exp = f.read()
    lines = exp.split()
    rec_os = False
    for line in lines:
        print(line)
        rec_os = id_recommendations(line)
        if rec_os:
            return rec_os
        else:
            continue


# Generate OS rec based on extension or file specs
def generate_os_rec(file):
    print("--READING FILE EXTENSIONS -- \n")
    if file.full_path.endswith('.rb'):
        return "Kali"
    elif file.full_path.endswith('.exe'):
        return "Windows7"
    test_os = find_test_os(file)
    if test_os:
        return test_os
    else:
        return default_os


# ID Recomendation
def id_recommendations(s):
    if "windows" or "windows7" in s.lower():
        return "Windows7"
    if "cent" or "centos" in s.lower():
        return "CentOS"
    if "kali" in s.lower():
        return "Kali"
    if "ubuntu" or "debian" in s.lower():
        return "Ubuntu"
    return False
