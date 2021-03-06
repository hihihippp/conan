import os
from conans.errors import ConanException
import logging
from conans.util.env_reader import get_env
from conans.util.files import save, load
from ConfigParser import NoSectionError, ConfigParser
from conans.model.values import Values

MIN_SERVER_COMPATIBLE_VERSION = '0.4.0'

default_settings_yml = """
os: [Windows, Linux, Macos, Android]
arch: [x86, x86_64, arm]
compiler:
    gcc:
        version: ["4.6", "4.7", "4.8", "4.9", "5.0"]
    Visual Studio:
        runtime: [None, MD, MT, MTd, MDd]
        version: ["8", "9", "10", "11", "12", "14"]
    clang:
        version: ["3.3", "3.4", "3.5", "3.6", "3.7"]
    apple-clang:
        version: ["5.0", "5.1", "6.0", "6.1", "7.0"]

build_type: [None, Debug, Release]
"""


default_client_conf = '''
[storage]
# This is the default path, but you can write your own
path: ~/.conan/data

[remotes]
conan.io: https://server.conan.io
local: http://localhost:9300

[settings_defaults]

'''


class ConanClientConfigParser(ConfigParser):

    def __init__(self, filename):
        ConfigParser.__init__(self)
        self.read(filename)

    def get_conf(self, varname):
        """Gets the section from config file or raises an exception"""
        try:
            return self.items(varname)
        except NoSectionError:
            raise ConanException("Invalid configuration, missing %s" % varname)

    @property
    def storage(self):
        return dict(self.get_conf("storage"))

    @property
    def storage_path(self):
        try:
            result = os.path.expanduser(self.storage["path"])
        except KeyError:
            result = None
        result = get_env('CONAN_STORAGE_PATH', result)
        return result

    @property
    def remotes(self):
        return self.get_conf("remotes")

    @property
    def settings_defaults(self):
        default_settings = self.get_conf("settings_defaults")
        values = Values.from_list(default_settings)
        return values
