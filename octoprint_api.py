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

class api(object):
    """
    Management and wrapper class for OctoPrint
    Note: All measuremets are in mm and all temperatures in
    degrees celsius!
    """

    def _set_url(self, base_url=None):
        """
        Initialize the API urls based on the base_url.
        base_url has to include the port information if not
        default http port (:80)
        """
        self._url = {'base':base_url, 'version':base_url+'/api/version',
            'files':base_url+'/api/files', 'files-sd':base_url+'/api/files/sd',
            'files-local':base_url+'/api/files/local',
            'connection':base_url+'/api/connection',
            'printer':base_url+'/api/printer',
            'printhead':base_url+'/api/printer/printhead',
            'tool':base_url+'/api/printer/tool',
            'bed':base_url+'/api/printer/bed',
            'sd':base_url+'/api/printer/sd',
            'command':base_url+'/api/printer/command'}

    def __init__(self, base_url=None, api_key='', debug=False):
        """
        Initialize the api object.
        base_url -- URL of the OctoPrint server, including port. Default: None
        api_key -- API key for accessing OctoPrint. Default: empty string
        debug -- Switch URL output on or off, default: False (no debug)
        """
        self._set_url(base_url=base_url)
        self._header = {'X-Api-Key':api_key, 'content-type':'application/json'}
        self._debug = debug

    @property
    def apikey(self):
        return(self._header['X-Api-Key'])

    @apikey.setter
    def apikey(self, api_key):
        self._header['X-Api-Key'] = api_key
        
    @property
    def url(self):
        return(self._url['base'])

    @url.setter
    def url(self, url_string):
        self._set_url(url_string)

    def _get_request(self, url=None, param=None):
        response = requests.get(url, headers=self._header, params=param)
        if response.status_code == 401:
            raise NotAuthorizedException(response)
        elif response.status_code >=400:
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
            return(response)
    
    def get_status(self, history=True, limit=2):
        """
        Get the status of the OctoPrint server.
        Parameters history and limit are for requesting temperature
        history data and limiting it to a given number of entries.
        Returns a dictionary with the current printer state.

        Otherwise raises an exception, either HTTPException
        or OctoprintException.
        """
        if history:
            hist_str = 'true'
        else:
            hist_str = 'false'
        param={'history':hist_str, 'limit':limit}
        r = self._get_request(self._url['printer'], param)
        return(r)

    def get_version(self):
        """
        Get version information of the OctoPrint server
        Otherwise raises an exception, either HTTPException
        or OctoprintException.
        """
        r = self._get_request(self._url['version'], None)
        return(r)

    def get_connection(self):
        """
        Get connetion information between OctoPrint server
        and printer.
        Otherwise raises an exception, either HTTPException
        or OctoprintException.
        """
        r = self._get_request(self._url['connection'], None)
        return(r)

    def home(self, x=None, y=None, z=None):
        """Homes the selected axes. Jus set the axis parameter
        you want to home.
        """
        home_set = []
        if x:
            home_set.append('x')
        if y:
            home_set.append('y')
        if z:
            home_set.append('z')
        request = {'command':'home','axes':home_set}
        r = self._post_request(self._url['printhead'], request)
        return(r)

    def jog(self, x=None, y=None, z=None):
        """Moves the print head a given amount in each given
        direction relative to the current position.
        May rise an exception, either HTTPException
        or OctoprintException (for example, when trying to jog
        when the printer is busy or disconnected).
        """
        request = {'command':'jog'}
        if x is not None:
            request['x'] = x
        if y is not None:
            request['y'] = y
        if z is not None:
            request['z'] = z
        r = self._post_request(self._url['printhead'], request)
        return(r)

    def extrude(self, amount=5):
        """Extrudes a given length of filament on the currently
        active extruder. Negative values are retractions.
        May rise an exception, either HTTPException
        or OctoprintException (for example when trying to extrude
        when the printer is busy or not connected).
        """
        request = {'command':'extrude','amount':amount}
        r = self._post_request(self._url['tool'], request)
        return(r)

    def set_tool_temp(self, temp=0, tool=0):
        """Sets the temperature of the given tool.
        Setting the temperature to 0 deactivates the heater.
        May rise an exception, either HTTPException
        or OctoprintException.
        """
        target_string = 'tool{0}'.format(tool)
        request = {'command':'target','targets':{target_string:temp}}
        r = self._post_request(self._url['tool'], request)
        return(r)

    def get_tool_temp(self, tool=0):
        """Gets the current temperature reading of the given tool.
        May rise either HTTPException or
        OctoprintException
        """
        target_string = 'tool{0}'.format(tool)
        param = {'history':'false', 'limit':2}
        r = self._get_request(self._url['tool'], param)
        if target_string in r['temps']:
            return(r['temps'][target_string])
        else:
            return(None)
        
    def set_bed_temp(self, temp=0):
        """Sets the heated bed temperature. Setting the temperature
        to 0 disables the bed heater.
        May rise either HTTPException or OctoprintException.
        """
        request = {'command':'target','target':temp}
        r = self._post_request(self._url['bed'], request)
        return(r)



if __name__ == '__main__':
    # for parsing the config file in self-test
    import xml.etree.ElementTree
    # for delay in self-test
    import time

    config = xml.etree.ElementTree.parse('octoprint_api.xml')
    item = config.find('octoprint')
    op = api(base_url=item.attrib['url'], api_key=item.attrib['apikey'], debug=True)
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
    print('Retrieveing connection')
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
    # print('Set bed temperature')
    # r = op.set_bed_temp(temp=60)
    # print(r)
    print('Get Tool 0 temp')
    r = op.get_tool_temp(tool=0)
    print(r)
    # print('Waiting one minute for temperatures to change, please wait')
    # time.sleep(60)
    # r = op.get_status()
    # print(r)
    op.set_bed_temp(temp=0)
    op.set_tool_temp(temp=0)
    r = op.get_status()
    print(r)
