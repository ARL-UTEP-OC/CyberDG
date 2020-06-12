from flask import Flask, render_template, redirect, request, url_for, flash, Response, send_file, jsonify
from werkzeug.utils import secure_filename
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.datastructures import CombinedMultiDict

from models import (db, Scenario, GuacUser, Machine, Run, Config, File, FileTypeEnum, OS,
                    MachineTypeEnum, NetworkTypeEnum)
from rdpManager import RDPManager
from loggers import initialize_logger
from vagrant_interface import VagrantInterface
from forms import FileUploadForm, NewScenarioForm, NewMachineForm, EditNetworkForm, ImportScenarioForm
from exporter import ScenarioSchema, FileSchema, MachineSchema

import scenario_gen
import machine_gen
import os
import io
import datetime
import hasher
import exporter
import zipfile
import json
from os.path import basename

app = Flask(__name__)

# configure db
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://db_admin:kdlsjfsdfds@db:5432/db_admin'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def flash_form_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{error}', 'danger')


def get_rdp_ip():
    vi = VagrantInterface()
    with open('../existing_network') as f:
        network = f.readline()
    print(network)
    ip = vi.get_rdp_ip(network)
    # if request.user_agent.platform.lower() == 'windows':
    #     ip = vi.get_rdp_ip("VirtualBox Host-Only Ethernet Adapter #2")
    # else:
    #     ip = vi.get_rdp_ip('vboxnet1')
    logger.info(ip)
    return ip


def get_files(form_exploits_data, form_vulns_data):
    files = form_exploits_data + form_vulns_data
    logger.info(files)
    file_list = []
    for file in files:
        f = File.query.filter_by(name=file).first()
        if f:
            file_list.append(f)
    return file_list


def get_files_from_scenario(scenario_id):
    files = Scenario.query.filter_by(id=scenario_id).first().file
    exploits = []
    vulns = []
    for file in files:
        if file.file_type == FileTypeEnum.pov:
            exploits.append(file)
        else:
            vulns.append(file)
    return (exploits, vulns)

#not used anymore
def get_files_from_machine(machine_id):
    files = Machine.query.filter_by(id=machine_id).first().file
    exploits = []
    vulns = []
    for file in files:
        if file.file_type == FileTypeEnum.pov:
            exploits.append(file)
        else:
            vulns.append(file)
    return (exploits, vulns)


def is_pyro_running(suppress_flash=False):
    error_message = 'Error: Could not connect to Pyro Server.  Please ensure it is running.'
    try:
        vi = VagrantInterface()
        if not vi.ping_pyro_server():
            raise Exception()
        return True
    except:
        if not suppress_flash:
            flash(error_message, 'danger')
        return False


@app.route('/')
def index():
    is_pyro_running()
    scenarios = Scenario.query.all()
    exploits = File.query.filter_by(file_type=FileTypeEnum.pov).all()
    vulns = File.query.filter_by(file_type=FileTypeEnum.vuln).all()
    return render_template('landing.html', scenarios=scenarios, exploits=exploits, vulns=vulns)


@app.route('/scenario/<id>')
def scenario(id):
    is_pyro_running()
    scenario = Scenario.query.filter_by(id=id).first()
    if not scenario:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Scenario Not Found',
                               message='Please check your url and try again')
    scenarios = Scenario.query.all()
    guacUser = GuacUser.query.filter_by(scenario_id=scenario.id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    exploits = File.query.filter_by(file_type=FileTypeEnum.pov).all()
    vulns = File.query.filter_by(file_type=FileTypeEnum.vuln).all()
    return render_template('landing.html',
                           scenarios=scenarios,
                           scenario=scenario,
                           machines=machines,
                           guacUser=guacUser,
                           exploits=exploits,
                           vulns=vulns)


@app.route('/new_scenario', methods=['GET', 'POST'])
def new_scenario():
    exploits = File.query.filter_by(file_type=FileTypeEnum.pov).all()
    vulns = File.query.filter_by(file_type=FileTypeEnum.vuln).all()
    if request.method == 'GET':
        is_pyro_running()
        return render_template('newScenario.html', exploits=exploits, vulns=vulns)
    else:
        form = NewScenarioForm(request.form)
        logger.info(request.form)
        if not is_pyro_running():
            return render_template('newScenario.html', exploits=exploits, vulns=vulns, form=form)
        if not form.validate():
            logger.info(form.errors)
            flash_form_errors(form)
            return render_template('newScenario.html', exploits=exploits, vulns=vulns, form=form)

        scenario = Scenario(name=form.name.data,
                            description=form.description.data,
                            cve_number=form.cve_number.data)

        files = get_files(form.exploits.data, form.vulns.data)
        scenario.file = files

        db.session.add(scenario)
        db.session.commit()
        rdpManager = RDPManager()
        rdpManager.add_user(scenario.id, scenario.id)
        guacUser = GuacUser(guac_username=scenario.id,
                            guac_password=scenario.id,
                            scenario_id=scenario.id)
        db.session.add(guacUser)
        db.session.commit()
        exploits = form.exploits.data

        for index, exploit in enumerate(exploits):
            f = File.query.filter_by(name=exploit).first()
            if f:
                rdp_ip = get_rdp_ip()
                os_rec = scenario_gen.generate_os_rec(f)
                rec_machine = Machine(name=scenario.name + '-Exploits' + str(index+1),
                                      scenario_id=scenario.id,
                                      rdp_ip=rdp_ip)
                rec_machine.file.append(f)
                db.session.add(rec_machine)
                db.session.commit()

                machine_gen.generate(scenario, rec_machine, os_rec, vulns)
                db.session.commit()
                rdpManager = RDPManager(username=scenario.id, password=scenario.id)
                rdpManager.add_connection(name=rec_machine.id,
                                          username=rec_machine.machine_username,
                                          password=rec_machine.machine_password,
                                          hostname=rec_machine.rdp_ip,
                                          port=rec_machine.rdp_port)
                print(scenario.id)
                # machine_gen.generate(scenario, rec_machine, os_rec, vulns)
                # db.session.commit()
                connection_id = rdpManager.get_connection_id(str(rec_machine.id))
                connection_link = rdpManager.get_connection_link(connection_id)
                # print(connection_link)
                rec_machine.connection_link = connection_link
                rec_machine.connection_id = connection_id
                db.session.commit()

        return redirect(url_for('configure', id=scenario.id))


@app.route('/edit_scenario/<id>', methods=['GET', 'POST'])
def edit_scenario(id):
    exploits = File.query.filter_by(file_type=FileTypeEnum.pov).all()
    vulns = File.query.filter_by(file_type=FileTypeEnum.vuln).all()
    scenario = Scenario.query.filter_by(id=id).first()
    if not scenario:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Scenario Not Found',
                               message='Please check your url and try again')

    if request.method == 'GET':
        return render_template('newScenario.html',
                                scenario=scenario,
                                exploits=exploits,
                                vulns=vulns)
    if request.method == 'POST':
        form = NewScenarioForm(request.form)
        logger.info(request.form)
        if not form.validate():
            logger.info(form.errors)
            flash_form_errors(form)
            return render_template('newScenario.html', exploits=exploits, vulns=vulns, form=form)

        #check that the files are not in associated to a machine
        files = get_files(form.exploits.data, form.vulns.data)
        for m in scenario.machine:
            for f in m.file:
                if(f not in files):
                    flash(f"File '{f.name}' cannot be removed. Remove it fist from machine '{m.name}'", 'danger')
                    return render_template('newScenario.html', exploits=exploits, vulns=vulns, form=form)

        scenario.file = files
        scenario.name = form.name.data
        scenario.description = form.description.data
        scenario.cve_number = form.cve_number.data
        db.session.commit()

        flash('Scenario updated', 'success')
        return redirect(url_for('scenario', id=scenario.id))


@app.route('/build/<id>')
def build_scenario(id):
    scenario = Scenario.query.filter_by(id=id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    try:
        vi = VagrantInterface()
        for machine in machines:
            machine_os = OS.query.filter_by(id=machine.os_id).first()
            vagr_key = machine_os.vagrant_key
            vi.write_vagrantfile(machine, vagr_key, scenario)
        vi.vagrant_up(scenario)
        return render_template('build_scenario.html',
                               scenario=scenario,
                               machines=machines, nummachines=len(scenario.machine))
    except Exception as e:
        flash('Could not connect to Pyro Server. Make sure it is running and try again.', 'danger')
        return redirect(url_for('simple_network_setup', id=id))


@app.route('/run/<id>')
def run_scenario(id):
    scenario = Scenario.query.filter_by(id=id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    try:
        vi = VagrantInterface()
        machines_status = []
        machines_status = vi.vagrant_status(scenario)
        halt = 0
        if machines_status:
            for m in machines_status:
                if 'poweroff' in m[0][1]:
                    halt = 1
                    vi.vagrant_halt(scenario)
                    time.sleep(5)
                    vi.vagrant_up(scenario)
                    time.sleep(30)
                    break
        for machine in machines:
            machine_os = OS.query.filter_by(id=machine.os_id).first()
            vagr_key = machine_os.vagrant_key
            vi.add_inline_commands(machine, vagr_key, scenario)
   
        vi.vagrant_provision(scenario)
        return render_template('runningScenario.html', scenario=scenario, machines=machines)

    except Exception as e:
        flash('Could not connect to Pyro Server. Make sure it is running and try again.', 'danger')
        return redirect(url_for('build_scenario', id=id))

@app.route('/stop/<id>')
def stop_scenario(id):
    scenario = Scenario.query.filter_by(id=id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    try:
        vi = VagrantInterface()
        vi.vagrant_halt(scenario)
        return render_template('runningScenario.html', scenario=scenario, machines=machines)

    except Exception as e:
        flash('Could not connect to Pyro Server. Make sure it is running and try again.', 'danger')
        return redirect(url_for('build_scenario', id=id))

@app.route('/simple_network/<id>')
def simple_network_setup(id):
    is_pyro_running()
    scenario = Scenario.query.filter_by(id=id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    return render_template('networkSetup.html', scenario=scenario, machines=machines)


@app.route('/advanced_network/<id>')
def advanced_network_setup(id):
    scenario = Scenario.query.filter_by(id=id).first()
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    return render_template('runScenario.html', scenario=scenario, machines=machines)


@app.route('/configure/<id>')
def configure(id):
    is_pyro_running()
    scenario = Scenario.query.filter_by(id=id).first()
    if not scenario:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Scenario Not Found',
                               message='Please check your url and try again')
    machines = Machine.query.filter_by(scenario_id=scenario.id).all()
    return render_template('configurationPage.html', scenario=scenario, machines=machines)


@app.route('/configure/<scenario_id>/machine/new', methods=['GET', 'POST'])
def new_machine(scenario_id):
    if request.method == 'POST':
        form = NewMachineForm(request.form)
        logger.info(request.form)
        if not form.validate() or not is_pyro_running():
            flash_form_errors(form)
            os_list = OS.query.all()
            exploits, vulns = get_files_from_scenario(scenario_id)
            return render_template('configMachine.html',
                                   scenario_id=scenario_id,
                                   os_list=os_list,
                                   machine_types=MachineTypeEnum,
                                   network_types=NetworkTypeEnum,
                                   form=form,
                                   exploits=exploits,
                                   vulns=vulns)
        rdp_ip = get_rdp_ip()
        machine = Machine(name=form.name.data,
                          machine_ip='',
                          rdp_ip=rdp_ip,
                          rdp_port=5000,
                          machine_type=form.machine_type.data,
                          processors=form.processors.data,
                          memory=form.memory.data,
                          scenario_id=scenario_id,
                          os_id=form.vm_os.data,
                          network_type=form.network_type.data,
                          cmd_line=form.cmd_line.data,
                          cmd_order=form.cmd_order.data)
        if form.network_name:
            machine.network_name = form.network_name.data
        files = get_files(form.exploits.data, form.vulns.data)
        machine.file = files
        db.session.add(machine)
        db.session.commit()

        scenario = Scenario.query.filter_by(id=scenario_id).first()
        machine1 = Machine.query.filter_by(id=machine.id).first()

        machine1.machine_ip = machine_gen.generate_ip(scenario.id, machine1.id)
        machine1.rdp_port = machine_gen.generate_port(machine.id)
        db.session.commit()

        rdpManager = RDPManager(username=scenario.id, password=scenario.id)
        rdpManager.add_connection(name=machine.id,
                                  username=machine.machine_username,
                                  password=machine.machine_password,
                                  hostname=machine.rdp_ip,
                                  port=machine.rdp_port)

        connection_id = rdpManager.get_connection_id(str(machine.id))
        connection_link = rdpManager.get_connection_link(connection_id)
        machine.connection_link = connection_link
        machine.connection_id = connection_id
        db.session.commit()

        flash("Machine created", 'success')
        return redirect(url_for('configure', id=scenario_id))
    if request.method == 'GET':
        is_pyro_running()
        os_list = OS.query.all()
        exploits, vulns = get_files_from_scenario(scenario_id)
        return render_template('configMachine.html',
                               scenario_id=scenario_id,
                               os_list=os_list,
                               machine_types=MachineTypeEnum,
                               network_types=NetworkTypeEnum,
                               exploits=exploits,
                               vulns=vulns)


@app.route('/configure/<scenario_id>/machine/<machine_id>', methods=['GET', 'POST'])
def edit_machine(scenario_id, machine_id):
    machine = Machine.query.filter_by(id=machine_id).first()
    scenario = Scenario.query.filter_by(id=scenario_id).first()
    if not machine:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Machine Not Found',
                               message='Please check your url and try again')
    if not scenario:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Scenario Not Found',
                               message='Please check your url and try again')
    if request.method == 'GET':
        is_pyro_running()
        os_list = OS.query.all()
        exploits, vulns = get_files_from_scenario(scenario_id)
        return render_template('configMachine.html',
                               scenario_id=scenario_id,
                               os_list=os_list,
                               machine_types=MachineTypeEnum,
                               network_types=NetworkTypeEnum,
                               machine=machine,
                               exploits=exploits,
                               vulns=vulns)
    if request.method == 'POST':
        form = NewMachineForm(request.form)
        if not form.validate() or not is_pyro_running():
            flash_form_errors(form)
            os_list = OS.query.all()
            exploits, vulns = get_files_from_scenario(scenario_id)
            return render_template('configMachine.html',
                                   scenario_id=scenario_id,
                                   os_list=os_list,
                                   machine_types=MachineTypeEnum,
                                   network_types=NetworkTypeEnum,
                                   form=form,
                                   exploits=exploits,
                                   vulns=vulns)
        # TODO: Update ip and port numbers
        machine.name = form.name.data
        machine.machine_type = form.machine_type.data
        machine.processors = form.processors.data
        machine.memory = form.memory.data
        machine.scenario_id = scenario_id
        machine.os_id = form.vm_os.data
        machine.network_type = form.network_type.data
        machine.is_base = form.is_base.data
        machine.cmd_line = form.cmd_line.data
        machine.cmd_order = form.cmd_order.data

        if form.network_name.data:
            machine.network_name = form.network_name.data
        files = get_files(form.exploits.data, form.vulns.data)
        machine.file = files
        db.session.commit()
        flash('Machine updated', 'success')
        return redirect(url_for('configure', id=scenario_id))


@app.route('/simple_network/<scenario_id>/machine/<machine_id>', methods=['GET', 'POST'])
def edit_simple_network(scenario_id, machine_id):
    machine = Machine.query.filter_by(id=machine_id).first()
    scenario = Scenario.query.filter_by(id=scenario_id).first()
    if not machine:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Machine Not Found',
                               message='Please check your url and try again')
    if not scenario:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Scenario Not Found',
                               message='Please check your url and try again')
    if request.method == 'GET':
        is_pyro_running()
        os_list = OS.query.all()
        return render_template('editNetwork.html',
                               scenario_id=scenario_id,
                               os_list=os_list,
                               machine_types=MachineTypeEnum,
                               network_types=NetworkTypeEnum,
                               machine=machine)
    if request.method == 'POST':
        form = EditNetworkForm(request.form)
        if not form.validate():
            flash_form_errors(form)
            os_list = OS.query.all()
            return render_template('editNetwork.html',
                                   scenario_id=scenario_id,
                                   machine=machine,
                                   machine_types=MachineTypeEnum,
                                   network_types=NetworkTypeEnum,
                                   form=form)

        machine.network_type = form.network_type.data
        machine.machine_ip = form.network_ip.data
        if form.network_name.data:
            machine.network_name = form.network_name.data
        db.session.commit()
        db.session.commit()
        flash('Machine updated', 'success')
        return redirect(url_for('simple_network_setup', id=scenario_id))


@app.route('/configure/machine/<id>')
def configure_machine(id):
    m = Machine.query.filter_by(id=id).first()
    if not m:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='Machine Not Found',
                               message='Please check your url and try again')
    return render_template('configMachine.html', machine=m)


@app.route('/edit_file/<id>', methods=['GET', 'POST'])
def edit_file(id):
    file = File.query.filter_by(id=id).first()
    if not file:
        return render_template('404.html',
                               error_number='Error 404',
                               error_text='File Not Found',
                               message='File could not be found. Please check your url and try again')
    if request.method == 'GET':
        with open(file.full_path, 'r') as old_file:
            toDisplay = old_file.read()
        return render_template('editFile.html', file=file, content=toDisplay)
    else:
        with open(file.full_path, 'w') as new_file:
            new_file.write(request.form.get('file_text'))
        with open(file.full_path, 'r') as hash_file:
            new_hash = hasher.hash(hash_file)
            h = File.query.filter(File.hash == new_hash, File.id != file.id).first()
            if h:
                flash(f'Error: Identical file already exists as {h.name}', 'danger')
            else:
                file.hash = new_hash
                db.session.commit()
                flash('File Updated', 'success')
        return redirect(url_for('index'))


@app.route('/file_upload', methods=['POST'])
def file_upload():
    if request.method == 'POST':
        logger.info(request.form)
        form = FileUploadForm(CombinedMultiDict((request.files, request.form)))
        file = request.files.get('file')
        form.hash.data = hasher.hash(file)
        logger.info(form.hash.data)
        if form.validate():
            logger.info('Form is valid')
            file.stream.seek(0)
            timestamp = int(datetime.datetime.now().timestamp())
            filename = str(timestamp) + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            logger.info(filename + ' Saved')
            db_file = File(name=form.upload_name.data,
                           cve_number=form.cve_number.data,
                           full_path=os.path.join(app.config['UPLOAD_FOLDER'], filename),
                           description=form.description.data,
                           file_type=form.upload_type.data,
                           hash=form.hash.data)
            db.session.add(db_file)
            db.session.commit()
            # logger.info(str(db_file) + ' saved to db')
            flash('File Uploaded', 'success')
        else:
            # logger.info(form.errors)
            flash_form_errors(form)
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('index'))


@app.route('/file_delete', methods=['POST'])
def file_delete():
    if request.method == 'POST':
        file_id = request.form.get('file_id')
        # logger.debug(f'Request to delete file {file_id}')
        file = File.query.filter_by(id=file_id).first()
        if file:
            scenarios = Scenario.query.filter(Scenario.file.any(id=file_id)).first()
            if scenarios:
                flash('Error: File is associated to a Scenario', 'danger')
            else:
                db.session.delete(file)
                db.session.commit()
                flash('File successfully deleted', 'success')
            # logger.debug('File deleted')
        else:
            flash('Error: File could not be found', 'danger')
            # logger.debug('File not found')
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('index'))


@app.route('/scenario_delete', methods=['POST'])
def scenario_delete():
    if request.method == 'POST':
        scenario_id = request.form.get('scenario_id')
        logger.debug(f'Request to delete scenario {scenario_id}')
        scenario = Scenario.query.filter_by(id=scenario_id).first()
        rdp_manager = RDPManager()
        if scenario:
            guac_usr = GuacUser.query.filter_by(scenario_id=scenario.id).first()
            rdp_manager.delete_user(guac_usr.guac_username)
            scenario_machines = Machine.query.filter_by(scenario_id=scenario.id)
            if scenario_machines:
                for m in scenario_machines:
                    rdp_manager.delete_connection(m.connection_id)
                    db.session.delete(m)
                    db.session.commit()

            db.session.delete(scenario)
            db.session.commit()

            logger.debug('Scenario deleted')
            flash('Scenario successfully deleted', 'success')
        else:
            flash('Error: Scenario could not be found', 'danger')
            logger.debug('Scenario not found')
        return redirect(url_for('index'))


@app.route('/machine_delete', methods=['POST'])
def machine_delete():
    rdp_manager = RDPManager()
    if request.method == 'POST':
        machine_id = request.form.get('machine_id')
        logger.debug(f'Request to delete file {machine_id}')
        machine = Machine.query.filter_by(id=machine_id).first()
        if machine:
            # connection_id = rdp_manager.get_connection_id(machine_id)
            rdp_manager.delete_connection(machine.connection_id)
            db.session.delete(machine)
            db.session.commit()
            logger.info(f'Deleted machine {machine.name}')
            flash(f'Successfully deleted machine {machine.name}', 'success')
        else:
            logger.info(f'Could not find machine {machine_id}')
            flash('Error: Machine could not be found', 'danger')
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('index'))


@app.route('/scenario_export/<id>')
def scenario_export(id):
    logger.info('Request to export scenario ' + id)
    jsonfiles = {}
    filesList = []
    #Schemas
    scenario_schema = ScenarioSchema()
    file_schema = FileSchema()
    machine_schema = MachineSchema()
    # Get scenario
    scenario = Scenario.query.filter_by(id=id).first()
    jsonfiles["scenario"]= scenario_schema.dump(scenario)
    # Get files
    files_data = []
    for i, f in enumerate(scenario.file):
        filesList.append(f.full_path)
        files_data.append(file_schema.dump(f))
    jsonfiles["files"]= files_data
    # Get machines
    machines_data = []
    for i, m in enumerate(scenario.machine):
        machines_data.append(machine_schema.dump(m))
    jsonfiles["machines"]= machines_data

    filename = scenario.name
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for key, jsonf in jsonfiles.items():
            zf.writestr(key+".json", json.dumps(jsonf, cls=exporter.EnumEncoder))
        for file in filesList:
            zf.write(file, basename(file))
    memory_file.seek(0)

    return send_file(memory_file,
                     as_attachment=True,
                     attachment_filename=filename + ".zip",
                     mimetype='application/zip')


@app.route('/scenario_import', methods=['POST'])
def scenario_import():
    if request.method == 'POST':
        logger.info(request.form)
        form = ImportScenarioForm(CombinedMultiDict((request.files, request.form)))
        if form.validate():
            scenarioname = form.name.data
            zip_file = request.files.get('file')
            file_extension = zip_file.filename.rsplit('.', 1)[1].lower()

            if file_extension == 'zip':
                with zipfile.ZipFile(zip_file, 'r') as myzip:
                    #for file in myzip.namelist():
                    scenariojson = exporter.extractJSONfile("scenario.json", myzip)
                    filesjson = exporter.extractJSONfile("files.json", myzip)
                    machinesjson = exporter.extractJSONfile("machines.json", myzip)

                    scenario_schema = ScenarioSchema()
                    file_schema = FileSchema()
                    machine_schema = MachineSchema()
                    if scenariojson and filesjson and machinesjson:
                        scenarioDB = scenario_schema.load(scenariojson, session=db.session)

                        exists = Scenario.query.filter_by(name=scenarioDB.name).first()
                        if exists:
                            flash('Scenario already exists!', 'danger')
                            return redirect(url_for('index'))

                        file_list = []
                        for fjson in filesjson:
                            fileDB = file_schema.load(fjson, session=db.session)
                            #check if file already exists using its hash
                            existingfile = File.query.filter_by(hash=fileDB.hash).first()
                            if existingfile:
                                file_list.append(existingfile)
                            else:
                                file = myzip.extract(os.path.basename(fileDB.full_path),
                                                                app.config['UPLOAD_FOLDER'])
                                fileDB.full_path = file
                                db.session.add(fileDB)
                                db.session.commit()
                                file_list.append(fileDB)

                        scenarioDB.file = file_list
                        scenarioDB.name = scenarioname
                        db.session.add(scenarioDB)
                        db.session.commit()

                        rdpManager = RDPManager()
                        rdpManager.add_user(scenarioDB.id, scenarioDB.id)
                        guacUser = GuacUser(guac_username=scenarioDB.id,
                                guac_password=scenarioDB.id,
                                scenario_id=scenarioDB.id)
                        db.session.add(guacUser)
                        db.session.commit()

                        for mjson in machinesjson:
                            os_id = mjson.pop('os')
                            machinefiles = mjson.pop('file')
                            lf = []
                            for f in machinefiles:
                                lf.append(File.query.filter_by(name=f).first())
                            machineDB = machine_schema.load(mjson, session=db.session)
                            machineDB.scenario_id = scenarioDB.id
                            machineDB.os_id = os_id
                            machineDB.file = lf
                            db.session.add(machineDB)
                            db.session.commit()
                            flash('Successfully imported scenario', 'success')
                    else:
                        flash('Invalid Zip File', 'danger')
            else:
                flash('File is not supported. Please, submit a ZIP file', 'danger')
        else:
            # logger.info(form.errors)
            flash_form_errors(form)
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('index'))


@app.route('/build_base_machine', methods=['POST'])
def build_base_machine():
    machine = Machine.query.filter_by(id=request.form.get('id')).first()
    if not machine:
        return Response(status=403)
    vm_name = f'{machine.name}-{machine.id}'
    base_name = request.form.get('name')
    os = OS(name=base_name, vagrant_key=base_name, is_base=True)
    db.session.add(os)
    db.session.commit()
    vi = VagrantInterface()
    vi.save_as_base(base_name, vm_name)
    return Response(status=200)


@app.route('/setup_db')
def setup_db():
    rdpManager = RDPManager()
    rdpManager.delete_all_users()
    rdpManager.delete_all_connections()
    os_types = [
        ('Ubuntu14.04(Server)', 'ubuntu/trusty64'),
        ('CentOS', 'centos/7'),
        ('Ubuntu16.04', "ubuntu/xenial64"),
        ('Windows7', "senglin/win-7-enterprise"),
        ('Kali', "kalilinux/rolling")
    ]
    count = db.session.query(OS.id).count()
    if count < 5:
        for os_type in os_types:
            try:
                o = OS(name=os_type[0], vagrant_key=os_type[1])
                db.session.add(o)
                db.session.commit()
            except:
                logger.info(f'{os_type[0]} is already in the database')
    flash('Database Populated', 'success')
    if request.referrer:
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))


@app.route('/ping')
def ping():
    if request.method == 'GET':
        return Response(status=200)


@app.route('/userManual')
def user_manual():
    return render_template('userManualPage.html', isNotNav=True)


@app.route('/<path:path>')
def catch_all(path):
    return render_template('404.html',
                           error_number='Error 404',
                           error_text='Page Not Found',
                           message='Please check your url and try again')

####################################################
# Do not place any routes below the above route!!! #
####################################################


if __name__ == '__main__':
    # create admin/views
    admin = Admin(app, name='Practicum', template_mode='bootstrap3')
    admin.add_view(ModelView(Scenario, db.session))
    admin.add_view(ModelView(GuacUser, db.session))
    admin.add_view(ModelView(Machine, db.session))
    admin.add_view(ModelView(Run, db.session))
    admin.add_view(ModelView(Config, db.session))
    admin.add_view(ModelView(File, db.session))
    admin.add_view(ModelView(OS, db.session))

    # create logger
    logger = initialize_logger()
    # sets up db
    # setup_db()
    # set up app
    app.secret_key = os.environ.get('SECRET_KEY')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
