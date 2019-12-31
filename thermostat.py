import sys
import requests
from requests.auth import HTTPBasicAuth


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
        try:
            r = requests.get(self._base_url.format(endpoint="api.html")[:-4])
            assert r.status_code == 200
        except Exception as e:
            raise type(e)("Connection to Thermostat failed with: {}".format(str(e))
                         ).with_traceback(sys.exc_info()[2])

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

        if 'params' in kwargs:
            kwargs['params']['sn'] = self.sn
        kwergs.update(kwargs)

        r = requests.post(self._get_url(endpoint), **kwergs)

        return r

    def status(self):
        """
        Get the status dictionary from the thermostat
        """
        r = self.post(params={"cmd": 4})
        return r.json()

    @property
    def temperature(self):
        """
        Current value of the temperature sensor in C
        """
        return float(self.status()['t.1']) / 100

    @property
    def setpoint(self):
        """
        Current thermostat setpoint in C
        """
        return float(self.status()['t.5']) / 100

    @setpoint.setter
    def setpoint(self, val):
        # val = int(val * 100)
        setpoint = str(val).encode()
        self.post(par=[[5,1,setpoint]])

    @property
    def mode(self):
        """
        Returns the current mode of the thermostat.
        Returns
        -------
        mode : `int`
            `0` for schedule mode, `3` for manual mode and `4` for away mode.
        """
        return self.status()['m.1']

    @mode.setter
    def mode(self, val):
        val = int(val)
        if val not in [0, 1]:
            raise ValueError("mode must be either 0,1")
        self.post(par=[[2,2,str(val).encode()]])

    @property
    def state(self):
        """
        Current state of the relay.
        Returns
        -------
        state : `bool`
            returns `True` if the relay is on and `False` if the relay is off.
        """
        return bool(self.status()['f.0'])

    def switch(self):
        """
        Change the state of the relay.
        """
        return self.post(par=[[125, 7, "0" if int(not self.state) else "1"]])

    def turn_on(self):
        return self.post(par=[[125, 7, "0"]])

    def turn_off(self):
        return self.post(par=[[125, 7, "1"]])
