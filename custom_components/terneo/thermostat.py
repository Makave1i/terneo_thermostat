import sys
import requests
import logging
import time

from requests.auth import HTTPBasicAuth
from simplejson.errors import JSONDecodeError

_LOGGER = logging.getLogger(__name__)


class Thermostat:
    """
    A class for interacting with the Terneo Thermostat's HTTP API.
    Parameters
    ----------
    serialnumber: `str`
        Serial Number of device
    host : `str`
        Hostname or IP address.
    port : `int` (optional)
        The port of the web server.
    username : `str` (optional)
        The username for HTTP auth.
    password : `str` (optional)
        The password for the HTTP auth.
    """

    def __init__(self, serialnumber, host, port=80, username=None, password=None):
        if username or password and not username and password:
            raise ValueError(
                "Username and Password must both be specified, if either are specified."
            )
        elif username or password:
            self.auth = HTTPBasicAuth(username, password)
        else:
            self.auth = None

        self.sn = serialnumber

        self._base_url = "http://{}:{}/{{endpoint}}.cgi".format(host, port)
        self._setpoint = None
        self._temperature = None
        self._mode = None
        self._state = None

        self._last_request = time.time()

        try:
            r = requests.get(self._base_url.format(endpoint="api.html")[:-4])
            assert r.status_code == 200
        except Exception as e:
            raise type(e)("Connection to Thermostat failed with: {}".format(str(e))).with_traceback(sys.exc_info()[2])

    def _get_url(self, endpoint):
        return self._base_url.format(endpoint=endpoint)

    def get(self, endpoint, **kwargs):
        """
        Perform a GET request
        Parameters
        ----------
        endpoint : `str`
            The endpoint to send the request to, will have 'cgi' appended to it.
        kwargs : `dict`
            All other kwargs are passed to `requests.get`
        Returns
        -------
        response : `requests.Response`
            The result of the request.
        """
        kwergs = {'auth': self.auth}
        kwergs.update(kwargs)

        r = requests.get(self._get_url(endpoint), **kwergs)
        return r

    def post(self, endpoint='api', **kwargs):
        """
        Perform a POST request
        Parameters
        ----------
        endpoint : `str`
            The endpoint to send the request to, will have 'cgi' appended to it.
        kwargs : `dict`
            All other kwargs are passed to `requests.post`
        Returns
        -------
        response : `requests.Response`
            The result of the request.
        """
        kwergs = {'auth': self.auth}

        kwergs.update(kwargs)

        start_time = time.time()
        if start_time - self._last_request < 1:
            time.sleep(1)

        try:
            r = requests.post(self._get_url(endpoint), timeout=5, **kwergs)
        except Exception as e:
            self._last_request = time.time()
            _LOGGER.error(e)
            return False
        end_time = time.time()
        self._last_request = end_time
        try:
            content = r.json()
        except JSONDecodeError:
            return False
        except Exception as e:
            _LOGGER.error(e)
            return False

        if content.get('status', '') == 'timeout':
            if 'sn' in kwargs['json']:
                kwargs['json']['sn'] = '...filtered...'
            _LOGGER.warning(f'terneo timeout: {kwargs}')
            return False

        return content

    def status(self):
        """
        Get the status dictionary from the thermostat
        """
        r = self.post(json={"cmd": 4, "sn": self.sn})
        return r

    def is_on(self):
        """
        getting power on/off for firmware 2.3
        :return: bool
        """
        r = self.post(json={"cmd": 1, "sn": self.sn})
        if r and 'par' in r:
            for a in r['par']:
                if a[0] == 125:
                    return a[2] == "0"
        return False

    @property
    def temperature(self):
        """
        Current value of the temperature sensor in C
        """
        if self._temperature is None:
            data = self.status()
            if data:
                self._temperature = self.get_temperature(data)
        return self._temperature

    @staticmethod
    def get_temperature(data):
        return float(data['t.1']) / 16

    @property
    def setpoint(self):
        """
        Current thermostat setpoint in C
        """
        if self._setpoint is None:
            data = self.status()
            if data:
                self._setpoint = self.get_setpoint(data)
        return self._setpoint

    @setpoint.setter
    def setpoint(self, val):
        setpoint = str(val)
        self.post(json=dict(sn=self.sn, par=[[125, 7, "0"], [2, 2, "1"], [5, 1, setpoint]]))

    @staticmethod
    def get_setpoint(data):
        return float(data['t.5']) / 16

    @property
    def mode(self):
        """
        Returns the current mode of the thermostat.
        Returns
        -------
        mode : `int`
            `0` for schedule mode, `3` for manual mode and `4` for away mode.
        """
        if self._mode is None:
            data = self.status()
            if data:
                self._mode = self.get_mode(data)
        return self._mode

    def get_mode(self, data):
        if 'f.16' in data:  # in firmware 2.4 was added new flag for power off/on
            is_on = int(data['f.16']) == 0
        else:
            is_on = self.is_on()

        if not is_on:
            return -1
        else:
            return int(data['m.1'])

    @mode.setter
    def mode(self, val):
        val = int(val)
        if val not in [0, 1]:
            raise ValueError("mode must be either 0,1")

        self.post(json=dict(sn=self.sn, par=[[125, 7, "0"], [2, 2, str(val)]]))

    @property
    def state(self):
        """
        Current state of the relay.
        Returns
        -------
        state : `bool`
            returns `True` if the relay is on and `False` if the relay is off.
        """
        if self._state is None:
            data = self.status()
            if data:
                self._state = self.get_state(data)
        return self._state

    @staticmethod
    def get_state(data):
        return int(data['f.0']) == 1

    def turn_on(self):
        return self.post(json=dict(sn=self.sn, par=[[125, 7, "0"]]))

    def turn_off(self):
        return self.post(json=dict(sn=self.sn, par=[[125, 7, "1"]]))

    def update(self):
        data = self.status()
        if data:
            self._setpoint = self.get_setpoint(data)
            self._temperature = self.get_temperature(data)
            self._mode = self.get_mode(data)
            self._state = self.get_state(data)
