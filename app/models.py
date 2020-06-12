from flask_sqlalchemy import SQLAlchemy
import datetime
from enum import Enum, unique
from sqlalchemy.ext.declarative import declarative_base

db = SQLAlchemy()
Base = declarative_base()


Machine_File_Use = db.Table('machine_file_use',
    db.Column('machine_id', db.Integer, db.ForeignKey('machine.id'), nullable=False),
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), nullable=False),
    db.PrimaryKeyConstraint('machine_id', 'file_id')
)

Scenario_File_Use = db.Table('scenario_file_use',
    db.Column('scenario_id', db.Integer, db.ForeignKey('scenario.id'), nullable=False),
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), nullable=False),
    db.PrimaryKeyConstraint('scenario_id', 'file_id')
)


@unique
class MachineTypeEnum(Enum):
    victim_attacker = 'Victim/Attacker'
    victim = 'Victim'
    attacker = 'Attacker'


@unique
class FileTypeEnum(Enum):
    vuln = 'vuln'
    pov = 'pov'


@unique
class NetworkTypeEnum(Enum):
    nat = 'NAT Network'
    internal = 'Default Internal Network'
    named_network = 'Named Internal Network'


class Scenario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.String(500), unique=False, nullable=True)
    cve_number = db.Column(db.String(30), unique=False, nullable=True)
    guacUser = db.relationship('GuacUser', backref='scenario', cascade='all, delete', lazy=True)
    machine = db.relationship('Machine', backref='scenario', cascade='all, delete', lazy=True)
    run = db.relationship('Run', backref='scenario', cascade='all, delete', lazy=True)
    file = db.relationship('File', secondary=Scenario_File_Use, backref='scenario')

    def __str__(self):
        return self.name


class GuacUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    guac_username = db.Column(db.String(50), unique=True, nullable=False)
    guac_password = db.Column(db.String(50), unique=False, nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id'), nullable=False)

    def __str__(self):
        return self.guac_username


class OS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    vagrant_key = db.Column(db.String(30), unique=True, nullable=False)
    machine = db.relationship('Machine', backref='os', cascade='all, delete', lazy=True)
    is_base = db.Column(db.Boolean, unique=False, default=False)

    def __str__(self):
        return self.name


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    name = db.Column(db.String(150), unique=True, nullable=False)
    machine_ip = db.Column(db.String(15), unique=False, nullable=True)
    rdp_ip = db.Column(db.String(15), unique=False, nullable=True)
    rdp_port = db.Column(db.Integer(), unique=False, nullable=True)
    machine_username = db.Column(db.String(50), default='vagrant', unique=False, nullable=False)
    machine_password = db.Column(db.String(50), default='vagrant', unique=False, nullable=False)
    machine_type = db.Column(db.Enum(MachineTypeEnum), default=MachineTypeEnum.victim_attacker, nullable=False)
    processors = db.Column(db.Integer, default=1, unique=False)
    memory = db.Column(db.Integer, default=1024, unique=False)
    network_type = db.Column(db.Enum(NetworkTypeEnum), default=NetworkTypeEnum.internal, nullable=False)
    network_name = db.Column(db.String(50), unique=False, nullable=True)
    cmd_line = db.Column(db.String(50), unique=False, nullable=True)
    cmd_order = db.Column(db.Integer(), unique=False, nullable=True)
    connection_id = db.Column(db.Integer, default=0, unique=False, nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id'), nullable=False)
    os_id = db.Column(db.Integer, db.ForeignKey(OS.id), nullable=True)
    config = db.relationship('Config', uselist=False, backref='machine', cascade='all, delete', lazy=True)
    file = db.relationship('File', secondary=Machine_File_Use, backref='machine')
    connection_link = db.Column(db.String(100), default='', unique=False, nullable=True)

    def __str__(self):
        return self.name


class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    name = db.Column(db.String(150), unique=False, nullable=False)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id'), nullable=False)

    def __str__(self):
        return self.name


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    packages = db.Column(db.String(500), unique=False, nullable=True)
    open_port = db.Column(db.String(500), unique=False, nullable=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    full_path = db.Column(db.String(450), unique=True, nullable=False)
    description = db.Column(db.String(500), unique=False, nullable=False)
    file_type = db.Column(db.Enum(FileTypeEnum), default=FileTypeEnum.vuln, nullable=False)
    cve_number = db.Column(db.String(30), unique=False, nullable=True)
    hash = db.Column(db.String(32), unique=True, nullable=False)

    def __str__(self):
        return self.name
