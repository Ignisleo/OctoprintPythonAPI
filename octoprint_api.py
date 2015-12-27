import json
import requests


class HTTPException(Exception):
    """Raise when a general HTTP error happened.
    """
    pass


class ServerNotFoundException(HTTPException):
    """Raise when server is not found
    """
    pass


class OctoprintException(Exception):
    """Base exception for OctoPrint errors.
    All other exceptions inherit from this.
    """
    pass


class NotAuthorizedException(OctoprintException):
    """Raise when API key not ok.
    """
    pass


class PrinterBusyException(OctoprintException):
    """Raise when Operation requires idle printer
    and printer is busy.
    """
    pass


class FileException(OctoprintException):
    """Raise when something goes wrong when handling files.
    """
    pass


class LocationException(FileException):
    """Raise when a wrong storage location is selected.
    """
    pass


class UnsupportedFileException(FileException):
    """Raise when trying to upload a file that is neither gcode nor stl.
    """
    pass


class Api(object):
    """
    Management and wrapper class for OctoPrint
    """

    def _set_url(self, base_url=None):
        """
        Initialize the API urls based on the base_url.
        base_url has to include the port information if not
        default http port (:80)
        """
        self._url = {'base': base_url,
                     'version': base_url + '/api/version',
                     'files': base_url + '/api/files',
                     'files-sd': base_url + '/api/files/sd',
                     'files-local': base_url + '/api/files/local',
                     'connection': base_url + '/api/connection',
                     'printer': base_url + '/api/printer',
                     'printhead': base_url + '/api/printer/printhead',
                     'tool': base_url + '/api/printer/tool',
                     'bed': base_url + '/api/printer/bed',
                     'sd': base_url + '/api/printer/sd',
                     'command': base_url + '/api/printer/command',
                     'job': base_url + '/api/job'}

    def __init__(self, base_url=None, api_key='', debug=False):
        """
        Initialize the api object.
        :rtype : API object for Octoprint control
        base_url -- URL of the OctoPrint server, including port. Default: None
        api_key -- API key for accessing OctoPrint. Default: empty string
        debug -- Switch URL output on or off, default: False (no debug)
        """
        self._set_url(base_url=base_url)
        self._header = {'X-Api-Key': api_key, 'content-type': 'application/json'}
        self._debug = debug

    @property
    def apikey(self):
        return self._header['X-Api-Key']

    @apikey.setter
    def apikey(self, api_key):
        self._header['X-Api-Key'] = api_key

    @property
    def url(self):
        return self._url['base']

    @url.setter
    def url(self, url_string):
        self._set_url(url_string)

    def _get_request(self, url=None, param=None):
        response = requests.get(url, headers=self._header, params=param)
        if response.status_code == 401:
            raise NotAuthorizedException(response)
        elif response.status_code >= 400:
            raise HTTPException(response)
        else:
            data = response.json()
            return data

    def _post_request(self, url=None, request=None):
        response = requests.post(url, headers=self._header,
                                 data=json.dumps(request))
        # Is printer busy?
        if response.status_code == 409:
            raise PrinterBusyException(response)
        # Did the Authorization fail?
        elif response.status_code == 401:
            raise NotAuthorizedException(response)
        # Did some other HTTP error happen?
        elif response.status_code >= 400:
            raise HTTPException(response)
        # Is response empty?
        else:
            return response

    def get_status(self, history=True, limit=2):
        """
        Get the status of the OctoPrint server.
        Returns a dictionary:
        {<json_decoded_data>}
        Otherwise raises an exception
        :param history:
        :param limit:
        :return:
        """
        if history:
            hist_str = 'true'
        else:
            hist_str = 'false'
        param = {'history': hist_str, 'limit': limit}
        return_val = self._get_request(self._url['printer'], param)
        return return_val

    def get_version(self):
        """
        Get version information of the OctoPrint server
        Otherwise raises an exception
        :return:
        """
        return_val = self._get_request(self._url['version'], None)
        return return_val

    def get_connection(self):
        """
        Get connection information between OctoPrint server
        and printer.
        Otherwise raises an exception.
        :return:
        """
        return_val = self._get_request(self._url['connection'], None)
        return return_val

    def home(self, x=None, y=None, z=None):
        """
        Home the printhead in the given axis.
        Any value different than 'None' will home the respective axis.
        :param x:
        :param y:
        :param z:
        :return:
        """
        home_set = []
        if x:
            home_set.append('x')
        if y:
            home_set.append('y')
        if z:
            home_set.append('z')
        request = {'command': 'home', 'axes': home_set}
        return_val = self._post_request(self._url['printhead'], request)
        return return_val

    def jog(self, x=None, y=None, z=None):
        """
        Moves the printhead the given values.
        Any value other than 'None' will move in the respective axis,
        all values are incremental.
        (e.g. x=10 followed by x=10 will move 20mm in sum)
        :param x:
        :param y:
        :param z:
        :return:
        """
        request = {'command': 'jog'}
        if x is not None:
            request['x'] = x
        if y is not None:
            request['y'] = y
        if z is not None:
            request['z'] = z
        return_val = self._post_request(self._url['printhead'], request)
        return return_val

    def extrude(self, amount=5):
        """
        Extrude <amount> mm of filament on the currently active extruder.
        Use negative values to retract.
        Defaults to 5mm extrusion.
        :param amount:
        :return:
        """
        request = {'command': 'extrude', 'amount': amount}
        return_val = self._post_request(self._url['tool'], request)
        return return_val

    def select_tool(self, tool=0):
        """
        Selects the active extruder
        :param tool: extruder number, starting with 0. Default=0
        :return: Whatever comes back...
        """
        request = {'command': 'select', 'tool': 'tool{0}'.format(tool)}
        return_val = self._post_request(self._url['tool'], request)
        return return_val

    def set_tool_temp(self, temp=0, tool=0):
        """
        Set Tool <tool> to Temperature <temp>.
        Defaults to tool 0 temperature 0 (off).
        :param temp:
        :param tool:
        :return:
        """
        target_string = 'tool{0}'.format(tool)
        request = {'command': 'target', 'targets': {target_string: temp}}
        return_val = self._post_request(self._url['tool'], request)
        return return_val

    def _get_temperatures(self, url, target_string):
        param = {'history': 'false', 'limit': 2}
        return_val = self._get_request(url, param)
        if target_string in return_val:
            return return_val[target_string]
        else:
            return None

    def get_tool_temp(self, tool=0):
        """
        Get the current temperature for tool <tool>.
        Returns a dictionary with the current and target temperature
        and the temperature offset.
        :param tool:
        :return:
        """
        target_string = 'tool{0}'.format(tool)
        return_val = self._get_temperatures(self._url['tool'], target_string)
        return return_val

    def set_bed_temp(self, temp=0):
        """
        Set the bed to <temp> degrees celsius.
        Defaults to 0 (bed off).
        :param temp:
        :return:
        """
        request = {'command': 'target', 'target': temp}
        return_val = self._post_request(self._url['bed'], request)
        return return_val

    def get_bed_temp(self):
        """
        Get the current bed temperature.
        Returns a dictionary with the current and target temperature
        and the temperature offset.
        :return:
        """
        target_string = 'bed'
        return_val = self._get_temperatures(self._url['bed'], target_string)
        return return_val

    def get_job_info(self):
        """
        Get information about the current job.
        Returns a dictionary with the job info.
        Refer to the Octoprint doc for version 1.2.6
        :return:
        """
        return_val = self._get_request(self._url['job'], None)
        return return_val

    def job_start(self):
        """
        Start the currently loaded job.
        :return:
        """
        request = {'command': "start"}
        return_val = self._post_request(self._url['job'], request)
        return return_val

    def job_restart(self):
        """
        Restart the currently running job.
        :return:
        """
        request = {'command': 'restart'}
        return_val = self._post_request(self._url['job'], request)
        return return_val

    def job_pause(self):
        """
        Pause the currently printing job.
        :return:
        """
        request = {'command': 'pause'}
        return_val = self._post_request(self._url['job'], request)
        return return_val

    def job_cancel(self):
        """
        Cancel the currently running job.
        """
        request = {'command': 'cancel'}
        return_val = self._post_request(self._url['job'], request)
        return return_val

    def get_connection_status(self):
        """
        Gets the current connection information
        :return:
        """
        return_val = self._get_request(self._url['connection'])
        return return_val

    def connect(self, port=None, baudrate=None, profile=None, save=None, autoconnect=None):
        """
        Connects to a printer
        :param port: Port to connect to
        :param baudrate:
        :param profile:
        :param save:
        :param autoconnect:
        :return:
        """
        request = {'command': 'connect'}
        if port:
            request['port'] = str(port)
        if baudrate:
            request['baudrate'] = str(baudrate)
        if profile:
            request['printerProfile'] = str(profile)
        if save:
            request['save'] = True
        if autoconnect:
            request['autoconnect'] = True
        return_val = self._post_request(self._url['connection'], request)
        return return_val

    def disconnect(self):
        """
        Disconnect from printer
        :return:
        """
        request = {'command': 'disconnect'}
        return_val = self._post_request(self._url['connection'], request)
        return return_val

    def get_files(self, location=None):
        """
        Get the information of all files on the system
        :param location: Location to list. 'local', 'sdcard' or None for all
        :return: file information dictionary
        """
        if location in ['local', 'sdcard']:
            url = '{0}/{1}'.format(self._url['files'], location)
        else:
            url = self._url['files']
        return_val = self._get_request(url)
        return return_val

    def select_file(self, name=None, location='local', start_print=False):
        """
        Selects a file for printing, either from local Octoprint file system or
        from SD card.
        :param name: File name
        :param location: Either 'locaL' or 'sdcard', default: 'local'
        :param start_print: Immediately start print, default: False
        :return:
        """
        request = {'command': 'select', 'print': start_print}
        request_url = '{0}/{1}/{2}'.format(self._url['files'], location, name)
        return_val = self._post_request(request_url, request)
        return return_val

    def job(self, command=None):
        """
        Control a job.
        Start starts to print the currently active file,
        restart restarts the print from the beginning,
        pause pauses or unpauses a job,
        cancel stops the currently active print job.

        An error is raised if there is:
        no file selected when starting,
        no job printing or paused when pausing,
        no current job paused when restarting,
        no print job running or paused when cancelling
        :param command: string, either start, restart, pause or cancel
        :return:
        """
        if command.lower() in ['start', 'cancel', 'restart', 'pause']:
            request = {'command': command.lower()}
            return_val = self._post_request(self._url['job'], request)
            return return_val

if __name__ == '__main__':
    # for parsing the config file in self-test
    import xml.etree.ElementTree
    # for delay in self-test
    import time

    config = xml.etree.ElementTree.parse('octoprint_api.xml')
    item = config.find('octoprint')
    op = Api(base_url=item.attrib['url'], api_key=item.attrib['apikey'], debug=True)
    print('API key: {0}'.format(op.apikey))
    apikey = op.apikey
    op.apikey = 'Romanes eunt domus'
    print('API key: {0}'.format(op.apikey))
    op.apikey = apikey
    print('Retrieving status')
    r = op.get_status()
    print(r)
    print('Retrieving version')
    r = op.get_version()
    print(r)
    print('Retrieving connection')
    r = op.get_connection()
    print(r)
    print('Homing axis')
    r = op.home(x=True, y=True)
    print(r)
    print('Setting Temp')
    r = op.set_tool_temp(temp=200)
    print(r)
    print('Reading tool status')
    r = op.get_status()
    print(r)
    print('Set bed temperature')
    r = op.set_bed_temp(temp=60)
    print(r)
    print('Get Tool 0 temp')
    r = op.get_tool_temp(tool=0)
    print(r)
    print('Waiting 30s for temperatures to change, please wait')
    time.sleep(30)
    r = op.get_status()
    print(r)
    op.set_bed_temp(temp=0)
    op.set_tool_temp(temp=0)
    r = op.get_status()
    print('Final state message:')
    print(r)
