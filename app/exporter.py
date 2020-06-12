from flask import flash
from sqlalchemy import inspect
import io, json
from flask_marshmallow import Marshmallow
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested, Related
from marshmallow import fields, Schema, pre_dump
from models import (db, Scenario, GuacUser, Machine, Run, Config, File, FileTypeEnum, OS,
                    MachineTypeEnum, NetworkTypeEnum)

PUBLIC_ENUMS = {
    'MachineTypeEnum': MachineTypeEnum,
    'FileTypeEnum': FileTypeEnum,
    'NetworkTypeEnum': NetworkTypeEnum,
}

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in PUBLIC_ENUMS.values():
            enum, value = str(obj).split(".")
            return value
        return json.JSONEncoder.default(self, obj)

#Marshmallow Schemas
class FileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = File
        load_instance = True
        exclude = ("id",)

class GuacUserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = GuacUser
    scenario = fields.Pluck(lambda:ScenarioSchema, "id")

class RunSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Run
    scenario = fields.Pluck(lambda:ScenarioSchema, "id")

class ConfigSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Config
    machine = fields.Pluck(lambda:MachineSchema, "id")

class OSSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = OS
    machine = fields.Pluck(lambda:MachineSchema, "id", many=True)

class MachineSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Machine
        load_instance = True
        exclude = ("id",)
    os = fields.Pluck(OSSchema, "id")
    file = fields.Pluck(FileSchema, "name", many=True)

class ScenarioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Scenario
        load_instance = True
        exclude = ("id",)

#Import functions

def extractJSONfile(filename, zipfile):
    try:
        with zipfile.open(filename, 'r') as jsonfile:
            jsonData = json.load(jsonfile)
            return jsonData
    except:
        return False
