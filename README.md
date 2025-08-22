# Bose REST API

Unofficial Bose REST API for Soundbars and Speakers (without Soundtouch series).

This project provides a REST API to Bose Soundbars and Speakers locally. This project implements the [pybose](https://github.com/cavefire/pybose) library by [Timo Christeleit](https://github.com/cavefire) and wraps the functionality into a neat FastAPI REST Interface.

BOSE requires you to have an account in order to control a soundbar / speaker. Even if you allow access for all users in the network, you still need to provide your account credentials. So this integration is making use of pybose's authentication. You can find more information about this in the  [pybose](https://github.com/cavefire/pybose) repository.

Currently, not all functionality of the Bose App is implemented. Feel free to submit pull requests.

## Supported Devices
All devices commected via WiFi and controllable using the BOSE App should work. Here is the list of devices, that have been tested:

* Bose Soundbar 500
* Bose Soundbar 700
* Bose Soundbar 900
* Bose Soundbar Ultra
* Home Speaker 300 
* Home Speaker 500
* Bose Music Amplifier
* Bose Portable Speaker


## Configuration
You need to confige your environment variables with host ip, GUID, and credentials of your BOSE cloud account. You can either set them via a file in app/.env or as system ENV vars (useful for Docker deployments).

| Month    | Example | Description |
| -------- | ------- | ------- |
| BOSE_USERNAME  | hans@gruber.example | Bose App User ID |
| BOSE_PASSWORD | HorseBatteryStaples | Bose App Password |
| BOSE_HOST    | 10.0.0.123 | local IP address of device |
| BOSE_DEVICE_ID    | abcdef1-12av-aa41-ab21-f2a2135113 | GUID of Bose device, visible in Bose App |
| BOSE_VOLUME_STEP    | 5 | Steps for volume_up/down shortcut |

## Running as Docker
```
docker pull simiko291/pybose-fastapi-wrapped:latest
docker run -d --name bose-rest --env-file .\my.env -p 8291:8291 simiko291/pybose-fastapi-wrapped
```

## Running locally
You can run a local FastAPI server using `fastapi dev speaker_api.py ` which will start a local server under [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The docs are available under  [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Disclaimer
This project is not affiliated with Bose Corporation. The API is reverse-engineered and may break at any time. Use at your own risk.

## License
This project is licensed under GNU GPLv3 - see the [LICENSE](LICENSE) file for details.