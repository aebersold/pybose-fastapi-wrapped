# Bose REST API

Unofficial Bose REST API for Soundbars and Speakers (without Soundtouch series).

This project provides a REST API to Bose Soundbars and Speakers locally. It implements the [pybose](https://github.com/cavefire/pybose) library by [Timo Christeleit](https://github.com/cavefire) and wraps the functionality into a neat FastAPI REST Interface. I use this API wrapper to control my soundbar using my Loxone Smart Home installation. If you want to use [Homeassistant](https://github.com/cavefire/Bose-Homeassistant), there is a separate integration available.

The Bose REST API requires you to have a Bose app account in order to control a soundbar / speaker. Even if you allow access for all users in the network, you still need to provide your account credentials. So this integration is making use of pybose's authentication. You can find more information about this in the  [pybose](https://github.com/cavefire/pybose) repository.

Currently, not all functionality of the Bose App is implemented. Feel free to submit pull requests.

## Supported Devices
All devices connected via WiFi/ethernet and controllable using the Bose App should work. Here is the list of devices, that have been tested:

* Bose Soundbar 500
* Bose Soundbar 700
* Bose Soundbar 900
* Bose Soundbar Ultra
* Home Speaker 300 
* Home Speaker 500
* Bose Music Amplifier
* Bose Portable Speaker


## How to use

### Running as Docker
```
docker pull simiko291/pybose-fastapi-wrapped:latest
docker run -d --name bose-rest --env-file .\my.env -p 8291:8291 simiko291/pybose-fastapi-wrapped
```

### Running locally
You can run a local FastAPI server using `fastapi dev speaker_api.py ` which will start a local server under [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The docs are available under [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Connecting to your speaker
To connect to your Bose device, you an use the `POST /initialize ` endpoint, and provide your Bose App credentials, host (i.e. IP address) and Bose Device ID (visibile in the Bose app). The connection will be cached for the duration of the runtime.

Alternatively, if your device and credentials are static, you can also confige your environment variables with the configuration. Either set them via a file in app/.env or as system ENV vars (useful for Docker deployments). If env vars are set, the Bose REST API will automaticaly connect to your speaker on startup.

| Variable    | Example | Description |
| -------- | ------- | ------- |
| BOSE_USERNAME  | hans@gruber.example | Bose App User ID |
| BOSE_PASSWORD | HorseBatteryStaples | Bose App Password |
| BOSE_HOST    | 10.0.0.123 | local IP address of device |
| BOSE_DEVICE_ID    | abcdef1-12av-aa41-ab21-f2a2135113 | GUID of Bose device, visible in Bose App |
| BOSE_VOLUME_STEP    | 5 | Steps for volume_up/down shortcut |


### Example Usage
```
# Get volume
curl "http://localhost:8000/audio/volume"

# Set volume
curl -X PUT "http://localhost:8000/audio/volume" \
     -H "Content-Type: application/json" \
     -d '{"volume": 50}'

# Play/Pause
curl -X POST "http://localhost:8000/playback/play"
curl -X POST "http://localhost:8000/playback/pause"
```

## Disclaimer
This project is not affiliated with Bose Corporation. The API is reverse-engineered and may break at any time. Use at your own risk.

## License
This project is licensed under GNU GPLv3 - see the [LICENSE](LICENSE) file for details.