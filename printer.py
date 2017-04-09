"""
printer.py: A command-line interface for 3D-printers using
the octoprint api via octoprint_api.py.

Basic configuration (url, api-key) is either done via
printer.cfg or via command-line arguments.
"""
import octoprint_api
import argparse
import ConfigParser
from ConfigParser import NoOptionError, NoSectionError

# constant definitions
_JOB_COMMAND_LIST = ['start', 'cancel', 'pause', 'restart']


def init_printer(arguments):
    """
    Returns an initialized Printer API object.
    :param arguments: object with members URL and APIKEY
    :return: initialized octoprint_api-Api object
    """
    printer = octoprint_api.Api(base_url=arguments.url, api_key=arguments.apikey)
    return printer


def home_func(arguments):
    printer = init_printer(arguments)
    (x, y, z) = (False, False, False)
    if 'x' in arguments.axis.lower():
        x = True
    if 'y' in arguments.axis.lower():
        y = True
    if 'z' in arguments.axis.lower():
        z = True
    printer.home(x, y, z)


def status_func(arguments):
    printer = init_printer(arguments)
    response = printer.get_status(limit=arguments.history, history=not arguments.no_history)
    if arguments.machine_readable:
        print(response)
    else:
        print('Printer status: {0}'.format(response['state']['text']))
        temps = response['temperature']
        t_keys = temps.keys()
        # Safety check that only temperature indices are left
        if 'history' in t_keys:
            t_keys.remove('history')
        # Put indices into nice sequence
        t_keys.sort()
        for k in t_keys:
            print('{2:5} temp: {0:5.1f} C; setpoint: {1:5.1f} C'.format(temps[k]['actual'],
                                                                        temps[k]['target'],
                                                                        k))


def jog_func(arguments):
    printer = init_printer(arguments)
    printer.jog(arguments.x, arguments.y, arguments.z)


def extrude_func(arguments):
    printer = init_printer(arguments)
    printer.extrude(arguments.amount)

    
def tool_func(arguments):
    printer = init_printer(arguments)
    printer.set_tool_temp(arguments.temperature, arguments.number)


def bed_func(arguments):
    printer = init_printer(arguments)
    printer.set_bed_temp(arguments.temperature)


def config_file_func(filename='printer.cfg'):
    cp = ConfigParser.RawConfigParser()
    cp.read(filename)
    ret_value = {}
    try:
        ret_value['url'] = cp.get('settings', 'baseurl')
    except (NoOptionError, NoSectionError):
        ret_value['url'] = None
    try:
        ret_value['apikey'] = cp.get('settings', 'apikey')
    except (NoOptionError, NoSectionError):
        ret_value['apikey'] = None
    return ret_value


def connection_func(arguments):
    printer = init_printer(arguments)
    if arguments.connect:
        printer.connect(port=arguments.port, baudrate=arguments.baudrate, profile=arguments.profile,
                        save=arguments.save, autoconnect=arguments.autoconnect)
    elif arguments.disconnect:
        printer.disconnect()
    else:
        connection_info = printer.get_connection_status()
        print(connection_info)


def job_control_func(arguments):
    printer = init_printer(arguments)
    if arguments.command in _JOB_COMMAND_LIST:
        command = arguments.command
    else:
        command = None
    return_val = printer.job(command=command)
    return return_val


def file_select_func(arguments):
    printer = init_printer(arguments)
    printer.select_file(name=arguments.filename,
                        location=arguments.location,
                        start_print=arguments.start_print)


def file_list_func(arguments):
    printer = init_printer(arguments)
    files = printer.get_files()
    if arguments.long:
        print(files)
    else:
        for fileitem in files['files']:
            print('{0}\t{1}\t{2}'.format(fileitem['name'], fileitem['size'], fileitem['origin']))


def parser_func():
    configfile = config_file_func()
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', '-u', default=configfile['url'],
                        help='Printer URL')
    parser.add_argument('--apikey', '-a', default=configfile['apikey'],
                        help='API key for printer access')
    subcommand = parser.add_subparsers()

    jog_parser = subcommand.add_parser('jog',
                                       help='Jog the given axis')
    jog_parser.add_argument('-x', type=int, help='Distance on x axis')
    jog_parser.add_argument('-y', type=int, help='Distance on y axis')
    jog_parser.add_argument('-z', type=int, help='Distance on z axis')
    jog_parser.set_defaults(func=jog_func)

    home_parser = subcommand.add_parser('home')
    home_parser.add_argument('axis')
    home_parser.set_defaults(func=home_func)

    status_parser = subcommand.add_parser('status',
                                          help='Get the status of the printer')
    status_parser.add_argument('--machine-readable', '-m', action='store_true',
                               help='Enable machine-readable (i.e. dictionary dump) output')
    status_parser.add_argument('--history', '-y', type=int, default=2,
                               help='Length of history (only relevant for machine-readable output)')
    status_parser.add_argument('--no_history', '-n', action='store_true',
                               help='Disable history output (only relevant for machine-readable output)')
    status_parser.set_defaults(func=status_func)

    tooltemp_parser = subcommand.add_parser('tool',
                                            help='Set tool temperature')
    tooltemp_parser.add_argument('--number', '-n', type=int, default=0,
                                 help='Extruder number, defaults to 0')
    tooltemp_parser.add_argument('temperature', type=int, default=0,
                                 help='Tool temperature (defaults to 0 (off))')
    tooltemp_parser.set_defaults(func=tool_func)

    bedtemp_parser = subcommand.add_parser('bed',
                                           help='Set bed temperature')
    bedtemp_parser.add_argument('temperature', type=int, default=0,
                                help='Temperature, defaults to 0 (bed off)')
    bedtemp_parser.set_defaults(func=bed_func)

    extrude_parser = subcommand.add_parser('extrude',
                                           help='Extrude from currently active extruder')
    extrude_parser.add_argument('amount', type=int, default=5,
                                help='Extrude length, negative values to retract (defaults to 5mm)')
    extrude_parser.set_defaults(func=extrude_func)

    connection_parser = subcommand.add_parser('connection',
                                              help='Connection handling')
    connection_mutex_group = connection_parser.add_mutually_exclusive_group()
    connection_mutex_group.add_argument('--connect', '-c', action='store_true',
                                        help='Connect to printer')
    connection_mutex_group.add_argument('--disconnect', '-d', action='store_true',
                                        help='Disconnect from printer')
    connection_parser.add_argument('--port', '-p',
                                   help='Port to connect to, default: last used port')
    connection_parser.add_argument('--baudrate', '-b',
                                   help='Baudrate to use')
    connection_parser.add_argument('--profile',
                                   help='Printer profile to use')
    connection_parser.add_argument('--save',
                                   help='Save connection settings')
    connection_parser.add_argument('--autoconnect',
                                   help='Auto connect on startup')
    connection_parser.set_defaults(func=connection_func)

    file_parser = subcommand.add_parser('file',
                                        help='File operations')
    file_subparser = file_parser.add_subparsers()
    file_select = file_subparser.add_parser('select',
                                            help='Select file for printing')
    file_select.add_argument('--print', '-p', action='store_true',
                             dest='start_print',
                             help='Start print after loading file')
    file_select.add_argument('--location', '-o', default='local',
                             choices=['local', 'sdcard'],
                             help='File location (local or SD card), defaults to local')
    file_select.add_argument('filename',
                             help='File name')
    file_select.set_defaults(func=file_select_func)
    file_list = file_subparser.add_parser('list',
                                          help='List files. Default: file name and location only')
    file_list.add_argument('--long', '-l', action='store_true',
                           help='Long information')
    file_list.add_argument('--location', '-o', choices=['local', 'sdcard'],
                           help='Location to list')
    file_list.set_defaults(func=file_list_func)

    job_parser = subcommand.add_parser('job',
                                       help='Job functions')
    job_parser.add_argument('command',
                            choices=_JOB_COMMAND_LIST,
                            help='Start, cancel, pause/unpause or restart a job')
    job_parser.set_defaults(func=job_control_func)

    args = parser.parse_args()
    try:
        args.func(args)
    except (octoprint_api.HTTPException, octoprint_api.OctoprintException) as e:
        print('Error executing command. Error information: {0}'.format(e))

if __name__ == '__main__':
    parser_func()
