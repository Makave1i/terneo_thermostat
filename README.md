# Terneo Thermostat
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Terneo Thermostat component for Home Assistant

required device firmware version 2.3

https://terneo-api.readthedocs.io/ru/latest/

>In firmware version 2.3, the ability to control the local network by default blocked for security reasons.

block removing - https://terneo-api.readthedocs.io/ru/latest/en/safety.html

Two possibilities for installation:
 - put `terneo` folder to the `custom_components` folder and reboot HA.
 - With HACS: go in HACS, click on Integrations, click on the three little dots at top of the screen and selection "custom repositories", add this github url, select "Integration" as repository, and click ADD. Then go to the Integrations tab of HACS, and install the "Terneo Thermostat" integration.

config example (`configuration.yaml`):

```
climate:
  - platform: terneo
    serial: 'DEVICE_SERIALNUMBER'
    host: 'DEVICE_IP'
```
serial number can be found on the page  http://`{device_ip}`/index.html
