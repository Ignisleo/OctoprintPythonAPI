# OctoprintPythonAPI
## Python API for the OctoPrint 3d printer server

This Python progam provides an object for controlling a 3D printer using OctoPrint as print server. Note: Work in progress, not all API functions are implemeted yet (e.g. file control is not yet able to upload files, but more will be added soon).

Usage: Put the octoprint_python_api.py in your search path, import it in your program and instantiate the object 'api'. It's member functions let you control your printer.

Configuration of Octoprint URL and API key is done via the calling program, either as parameter to the constructor during intstantiating or later on by setting the appropriate variables. For testing purposes a xml configuration file can be provided. This file is only read when the module is started as stand-alone program.

The error handling is done by raising exceptions. There are two kind of exceptions currently, HTTP exceptions for signalling errors on the HTTP side (like wrong URL and such), and Octoprint exceptions for signalling something didn't go as planned with the command requested. If there is no consistent data, there is an exception.

## Command-line interface:
Apart from the Python bindings there is a command-line interface to control the printer from the command line using the Python script "printer.py".

### Configration for commad-line interface:
Either give the URL and the API key as parameters (see 'printer.py --help') or store the values in a 'printer.cfg' file

### Help on the command-line interface:
To get help on the command-line interface type:
`python printer.py --help`
