import sys
import requests
import logging
import time

from requests.auth import HTTPBasicAuth

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
        self._in_progress = False
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

        if 'json' in kwargs:
            kwargs['json']['sn'] = self.sn
        kwergs.update(kwargs)
        # _LOGGER.info(f'last request time - {self._last_request} - {time.time() - self._last_request}: {kwargs}')
        if time.time() - self._last_request < 1 or self._in_progress:
            time.sleep(1)

        try:
            r = requests.post(self._get_url(endpoint), **kwergs)
        except Exception as e:
            self._last_request = time.time()
            _LOGGER.error(e)
            return False

        content = r.json()
        self._last_request = time.time()

        return content

    def status(self):
        """
        Get the status dictionary from the thermostat
        """
        r = self.post(json={"cmd": 4})
        return r

    def is_on(self):
        r = self.post(json={"cmd": 1})
        if r and 'par' in r:
            for a in r['par']:
                if a[0] == 125:
                    return a[2] == "0"

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

    def get_temperature(self, data):
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
        self._setpoint = float(val)
        self.post(json=dict(par=[[125, 7, "0"], [2, 2, "1"], [5, 1, setpoint]]))

    def get_setpoint(self, data):
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
        if not self.is_on():
            return False
        return int(data['m.1'])

    @mode.setter
    def mode(self, val):
        val = int(val)
        if val not in [0, 1]:
            raise ValueError("mode must be either 0,1")

        self._mode = 3 if val == 1 else 0

        self.post(json=dict(par=[[125, 7, "0"], [2, 2, str(val)]]))

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

    def get_state(self, data):
        return int(data['f.0']) == 1

    def turn_on(self):
        return self.post(json=dict(par=[[125, 7, "0"]]))

    def turn_off(self):
        self._mode = False
        return self.post(json=dict(par=[[125, 7, "1"]]))

    def update(self):
        if time.time() - self._last_request > 10:
            data = self.status()
        else:
            time.sleep(1)
            data = self.status()

        if data:
            self._setpoint = self.get_setpoint(data)
            self._temperature = self.get_temperature(data)
            self._mode = self.get_mode(data)
            self._state = self.get_state(data)