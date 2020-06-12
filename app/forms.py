from wtforms import Form, FileField, validators, StringField, ValidationError, IntegerField, BooleanField, SelectMultipleField
from models import File, Scenario, Machine, OS, MachineTypeEnum, NetworkTypeEnum, FileTypeEnum
import re


class Unique(object):
    """ validator that checks field uniqueness """
    def __init__(self, model, field, message=None):
        self.model = model
        self.field = field
        if not message:
            message = 'This element already exists'
        self.message = message

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            if str(check.id) == form.id.data:
                print('form id', form.id.data)
            else:
                raise ValidationError(self.message)


class ValidOS(object):
    """validator that checks for a valid OS"""
    def __init__(self):
        pass

    def __call__(self, form, field):
        check = OS.query.filter(OS.id == field.data).first()
        if not check:
            raise ValidationError("Please select a valid OS.")


class ValidEnumType(object):
    """validator that checks for a valid enum type"""
    def __init__(self, enum, message=None):
        self.enum = enum
        if not message:
            message = 'This is not a valid value'
        self.message = message

    def __call__(self, form, field):
        if field.data not in self.enum.__members__:
            raise ValidationError(self.message)


class ValidNetworkName(object):
    """checks for a network name if Named Network is selected"""
    def __init__(self):
        pass

    def __call__(self, form, field):
        if form.network_type.data == 'named_network':
            if field.data == '':
                raise ValidationError('Please provide a name for the network')


class ValidName(object):
    """ validator that checks field uniqueness """
    def __init__(self, message=None):
        if not message:
            message = 'Names can only contain letters, numbers, and hyphens.'
        self.message = message

    def __call__(self, form, field):
        if not re.match("^[A-Za-z0-9-]*$", field.data):
            raise ValidationError(self.message)


class ValidCVE(object):
    """validator that checks for a valid cve number"""
    def __init__(self):
        pass

    def __call__(self, form, field):
        cve_format = re.compile('\d{4}-\d{4,7}')
        if len(field.data) > 12 or not cve_format.match(field.data):
            raise ValidationError("please enter valid CVE Number")

class MultipleField(SelectMultipleField):
    def pre_validate(self, form):
        """per_validation is disabled"""

class FileUploadForm(Form):
    upload_type = StringField('File Type', validators=[validators.required('Please provide a file type.'),
                                                       ValidEnumType(FileTypeEnum,
                                                       'Please select a valid file type')])
    upload_name = StringField('Name', validators=[validators.required(),
                                                  Unique(File, File.name,
                                                  'File names must be unique. Please choose a new name.')])
    file = FileField('File', validators=[validators.required()])
    hash = StringField('hash', validators=[Unique(File, File.hash, 'This file already exists')])
    id = StringField('File id')
    cve_number = StringField('CVE Number', validators=[validators.Optional(strip_whitespace=True),
                                                       ValidCVE()])
    description = StringField('Description', validators=[validators.required()])


class NewScenarioForm(Form):
    id = StringField('Scenario id')
    name = StringField('Name', validators=[validators.required('Please provide a name for the scenario.'),
                                           Unique(Scenario, Scenario.name,
                                           'Scenario names must be unique. Please choose a new name.'),
                                           ValidName()])
    cve_number = StringField('CVE Number',
                             validators=[validators.Optional(strip_whitespace=True), ValidCVE()])
    description = StringField('Description',
                              validators=[validators.required(
                                    'Please provide a description of the scenario.')])
    vulns = MultipleField('Vulnerabilities', choices=[])
    exploits = MultipleField('Exploits', choices=[])

class ImportScenarioForm(Form):
    id = StringField('Scenario id')
    name = StringField('Name', validators=[validators.required('Please provide a name for the scenario.'),
                                           Unique(Scenario, Scenario.name,
                                           'Scenario names must be unique. Please choose a new name.')])
    file = FileField('File', validators=[validators.required()])

class NewMachineForm(Form):
    id = StringField('Machine id')
    name = StringField('Name', validators=[validators.required('Please provide a name for the machine.'),
                                           Unique(Machine, Machine.name,
                                           'Machine names must be unique. Please choose a new name.'),
                                           ValidName()])
    machine_type = StringField('Machine Type',
                               validators=[validators.required('Please provide a machine type.'),
                                           ValidEnumType(MachineTypeEnum,
                                           'Please select a valid machine type')])
    processors = IntegerField('Processors',
                              validators=[
                                validators.required('Please provide a number of processors.'),
                                validators.NumberRange(min=1,
                                                       max=4,
                                                       message='Each machine can have between 1 and 4 procesors.')])
    memory = IntegerField('Memory',
                          validators=[
                            validators.required('Please specify how much memory to allocate.'),
                            validators.NumberRange(min=512,
                                                   max=16384,
                                                   message='Please select a memory allocation between 512 MB and 16384 MB.')])
    vm_os = IntegerField('OS',
                         validators=[
                            validators.required('Please select a valid OS for the machine.'),
                            ValidOS()])
    network_type = StringField('Network Type',
                               validators=[
                                    validators.required('Please provide a network type.'),
                                    ValidEnumType(NetworkTypeEnum, 'Please select a valid network type')])
    network_name = StringField('Network Name', validators=[ValidNetworkName()])
    is_base = BooleanField('Base')
    cmd_line = StringField('Command Prompts', validators=[validators.Optional(strip_whitespace=True)])
    cmd_order = IntegerField('Command Line Order', validators=[validators.Optional(strip_whitespace=True)])
    vulns = MultipleField('Vulnerabilities', choices=[])
    exploits = MultipleField('Exploits', choices=[])


class EditNetworkForm(Form):
    network_type = StringField('Network Type',
                               validators=[
                                    validators.required('Please provide a network type.'),
                                    ValidEnumType(NetworkTypeEnum, 'Please select a valid network type')])
    network_name = StringField('Network Name', validators=[ValidNetworkName(), ValidName()])
    network_ip = StringField('IP',
                             validators=[validators.Optional(strip_whitespace=True),
                                         validators.IPAddress(ipv4=True, ipv6=False, message='Please enter a valid IP Address')])
