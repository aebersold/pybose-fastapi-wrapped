"""
FastAPI REST API for Bose Speaker Control
Based on the BoseSpeaker class with WebSocket communication
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv
from pathlib import Path
import asyncio, json, os
import logging
from contextlib import asynccontextmanager

# Import your pybose
from pybose import BoseSpeaker, BoseAuth
from pybose.BoseSpeaker import (
    BoseFunctionNotSupportedException,
    BoseCapabilitiesNotLoadedException,
    BoseInvalidAudioSettingException,
    BoseRequestException,
)

# load .ENV
load_dotenv()
VOLUME_STEP = os.getenv('BOSE_VOLUME_STEP', 5)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global speaker instance, Auth object
speaker_instance: Optional[BoseSpeaker] = None
bose_auth = BoseAuth()
preset = None

# Pydantic models for request/response
class SpeakerConfig(BaseModel):
    email: str = Field(..., description="E-Mail address of users Bose App login")
    password: str = Field(..., description="Password of users Bose App login")
    host: str = Field(..., description="Speaker IP address or hostname")
    device_id: Optional[str] = Field(None, description="Device ID (optional)")
    version: int = Field(1, description="API version")
    auto_reconnect: bool = Field(True, description="Enable auto-reconnect")

class VolumeRequest(BaseModel):
    volume: int = Field(..., ge=0, le=100, description="Volume level (0-100)")

class MuteRequest(BaseModel):
    muted: bool = Field(..., description="Mute state")

class PowerRequest(BaseModel):
    state: bool = Field(..., description="Power state (true=on, false=off)")

class SeekRequest(BaseModel):
    position: Union[float, int] = Field(..., description="Position in seconds")

class PresetRequest(BaseModel):
    preset: int = Field(..., ge=1, le=6, description="Preset 1-6")

class SourceRequest(BaseModel):
    source: str = Field(..., description="Source name")
    source_account: str = Field(..., description="Source account")

class AudioSettingRequest(BaseModel):
    value: int = Field(..., description="Audio setting value")

class AudioModeRequest(BaseModel):
    mode: str = Field(..., description="Audio mode")

class DualMonoRequest(BaseModel):
    value: Union[int, str] = Field(..., description="Dual mono setting")

class RebroadcastLatencyRequest(BaseModel):
    mode: str = Field(..., description="Rebroadcast latency mode")

class AccessoriesRequest(BaseModel):
    subs_enabled: Optional[bool] = Field(None, description="Enable subwoofers")
    rears_enabled: Optional[bool] = Field(None, description="Enable rear speakers")

class ActiveGroupRequest(BaseModel):
    other_product_ids: List[str] = Field(..., description="List of other product IDs")

class ActiveGroupModifyRequest(BaseModel):
    active_group_id: str = Field(..., description="Active group ID")
    other_product_ids: List[str] = Field(..., description="List of product IDs")

class SystemTimeoutRequest(BaseModel):
    no_audio: bool = Field(..., description="No audio timeout")
    no_video: bool = Field(..., description="No video timeout")

class CecSettingsRequest(BaseModel):
    mode: str = Field(..., description="CEC mode")

class SubscribeRequest(BaseModel):
    resources: Optional[List[str]] = Field(None, description="List of resources to subscribe to")


# read .env config and chache for lifecylce of app, if it is present
if "BOSE_HOST" in os.environ:
    dotenv_config = SpeakerConfig(
        email=os.getenv('BOSE_USERNAME'),
        password=os.getenv('BOSE_PASSWORD'),
        host=os.getenv('BOSE_HOST'),
        device_id=os.getenv('BOSE_DEVICE_ID'),
        version=1,
        auto_reconnect=True
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global speaker_instance
    global dotenv_config
    logger.info("FastAPI application starting up")
    
    # auto initalize if .ENV vars are set
    if dotenv_config:
        await initialize_speaker(dotenv_config)

    yield
    logger.info("FastAPI application shutting down")
    if speaker_instance:
        # for some reason speaker_instance.disconnect() is broken - probably an issue with pybose?
        pass

        # try:
        #     await speaker_instance.disconnect()
        # except Exception as e:
        #     logger.error(f"Error disconnecting speaker: {e}")


# Create FastAPI app
try: 
    description = Path('../README.md').read_text()
except:
    description = ''
app = FastAPI(
    title="Bose Speaker API",
    description=description,
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/initialize", summary="Initialize Speaker Connection")
async def initialize_speaker(config: SpeakerConfig):
    """Initialize the Bose speaker connection"""
    global speaker_instance
    global bose_auth 
    global preset
    
    try:
        try:
            bose_auth.getControlToken(config.email, config.password)
            logger.info("Bose auth success")
        except Exception as e:
            logger.error(f"failed to authenticate with bose login: {e}")
            raise ValueError(f"failed to authenticate with bose login")
        
        speaker_instance = BoseSpeaker(
            host=config.host,
            device_id=config.device_id,
            version=config.version,
            auto_reconnect=config.auto_reconnect,
            bose_auth=bose_auth
        )
        
        await speaker_instance.connect()
        preset = await speaker_instance.get_product_settings()

        return {"status": "connected", "device_id": speaker_instance.get_device_id()}
    
    except Exception as e:
        logger.error(f"Failed to initialize speaker: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "InitializationError",
                "message": f"Failed to initialize speaker: {str(e)}",
                "code": 500
            }
        )

@app.post("/disconnect", summary="Disconnect Speaker")
async def disconnect_speaker():
    """Disconnect from the speaker"""
    global speaker_instance
    
    if not speaker_instance:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "SpeakerNotInitialized",
                "message": "Speaker not initialized",
                "code": 400
            }
        )
    
    try:
        await speaker_instance.disconnect()
        speaker_instance = None
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "DisconnectionError",
                "message": str(e),
                "code": 500
            }
        )

# Helper function to check speaker initialization
def check_speaker_initialized():
    # not inizialized
    if not speaker_instance:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "SpeakerNotInitialized",
                "message": "Speaker not initialized. Please call /initialize first.",
                "code": 400
            }
        )
    
    # check if token is expired and refresh
    if not bose_auth.is_token_valid():
        logger.info("Bose auth token expired, refreshing token...")
        bose_auth.do_token_refresh()

# Helper function to match now playing vs. presets 
def find_current_preset(now_playing: dict, presets_data: dict) -> int:
    """
    Match the currently playing station/source against presets.
    Prioritize 'sourceAccount'; use 'location' only if multiple presets share the same account.
    Returns preset number as int, or 0 if no match is found.
    """
    # Get contentItem from now playing JSON
    np_item = now_playing.get("container", {}).get("contentItem", {})
    np_account = np_item.get("sourceAccount")
    np_location = np_item.get("location")

    # Get all presets
    presets = presets_data.get("presets", {}).get("presets", {})

    # First, find all presets with the same sourceAccount
    matching_presets = []
    for preset_number, preset in presets.items():
        actions = preset.get("actions", [])
        for action in actions:
            content_item = action.get("payload", {}).get("contentItem", {})
            preset_account = content_item.get("sourceAccount")
            if preset_account == np_account:
                matching_presets.append((int(preset_number), content_item))

    if not matching_presets:
        return 0  # No match by account

    # If only one preset matches the account, return it
    if len(matching_presets) == 1:
        return matching_presets[0][0]

    # If multiple presets share the same account, further filter by location
    for preset_number, content_item in matching_presets:
        preset_location = content_item.get("location")
        if preset_location == np_location:
            return preset_number

    # If none match location, return the first matching account
    return matching_presets[0][0]


# Connection Management
@app.get("/device-id", summary="Get Device ID")
async def get_device_id():
    """Get the device ID"""
    check_speaker_initialized()
    
    device_id = speaker_instance.get_device_id()
    return {"device_id": device_id}

@app.get("/system/info", summary="Get System Information")
async def get_system_info():
    """Retrieve system information"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_system_info()
    return result

@app.get("/system/capabilities", summary="Get System Capabilities")
async def get_capabilities():
    """Retrieve device capabilities"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_capabilities()
    return result

# Product Settings
@app.get("/system/product-settings", summary="Get Product Settings")
async def get_product_settings():
    """Retrieve the product settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_product_settings()
    return result

# System Settings
@app.get("/system/timeout", summary="Get System Timeout")
async def get_system_timeout():
    """Retrieve the system timeout settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_system_timeout()
    return result

@app.put("/system/timeout", summary="Set System Timeout")
async def set_system_timeout(request: SystemTimeoutRequest):
    """Set system timeout settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_system_timeout(request.no_audio, request.no_video)
    return result

# Power Control
@app.get("/power", summary="Get Power State")
async def get_power_state():
    """Retrieve the power state of the device"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_power_state()
    return result

@app.post("/power", summary="Set Power State")
async def set_power_state(request: PowerRequest):
    """Set the device power state"""
    check_speaker_initialized()
    
    await speaker_instance.set_power_state(request.state)
    return {"status": "success", "power_state": request.state}

# Audio Volume Control
@app.get("/audio/volume", summary="Get Audio Volume")
async def get_audio_volume():
    """Retrieve the current audio volume"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_audio_volume()
    return result

@app.put("/audio/volume", summary="Set Audio Volume")
async def set_audio_volume(request: VolumeRequest):
    """Set the audio volume to the specified value"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_audio_volume(request.volume)
    return result

@app.put("/audio/volume/up", summary="Increase Audio Volume by configured step size")
async def set_audio_volume_up():
    """Set the audio volume to the specified value"""
    check_speaker_initialized()
    cur = await speaker_instance.get_audio_volume()
    result = await speaker_instance.set_audio_volume(min(100, cur['value'] + VOLUME_STEP))
    return result

@app.put("/audio/volume/down", summary="Decrease Audio Volume by configured step size")
async def set_audio_volume_up():
    """Set the audio volume to the specified value"""
    check_speaker_initialized()
    cur = await speaker_instance.get_audio_volume()
    result = await speaker_instance.set_audio_volume(max(0, cur['value'] - VOLUME_STEP))
    return result

@app.put("/audio/volume/mute", summary="Set Audio Mute")
async def set_audio_volume_muted(request: MuteRequest):
    """Set the audio volume muted state"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_audio_volume_muted(request.muted)
    return result

# Content and Playback Control
@app.get("/content/now-playing", summary="Get Now Playing")
async def get_now_playing():
    """Retrieve the currently playing content"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_now_playing()
    return result

# Content and Playback Control
@app.get("/playback/status", summary="Get Playback Status")
async def get_playback_status():
    """Retrieve the currently playback status"""
    check_speaker_initialized()
    global preset
    power = await speaker_instance.get_power_state()
    playback = await speaker_instance.get_now_playing()
    
    state = 0
    preset_number_playing = 0
    source = ''

    if playback.get("state") and playback["state"].get('status') == 'PLAY':
            state = 1
            preset_number_playing = find_current_preset(playback, preset)
    
    if playback.get("source") and playback["source"].get('sourceDisplayName'):
        mapping  = {
            "INVALID_SOURCE": 0,
            "AVSSIPSOURCE": 1,
            "AIRPLAY": 2,
            "CHROMECASTBUILTIN": 3,
            "GVA": 4,
            "SPOTIFY": 5,
            "GROUPING": 6,
            "ALEXA": 7,
            "QPLAY": 8,
            "UPNP": 9,
            "PRODUCT": 10, # TV
            "SETUP": 11,
            "BLUETOOTH": 12,
            "TUNEIN": 13 # web radio
        }
        source = mapping.get(playback["source"].get('sourceDisplayName').upper(), 0)  # 0 is default

    return {
        "power_state": power.get('power'),
        "playback": state,
        "source": source,
        "preset_number": preset_number_playing
    }

@app.post("/playback/play", summary="Play")
async def play():
    """Resume playback"""
    check_speaker_initialized()
    
    result = await speaker_instance.play()
    return result

@app.post("/playback/pause", summary="Pause")
async def pause():
    """Pause playback"""
    check_speaker_initialized()
    
    result = await speaker_instance.pause()
    return result

@app.post("/playback/skip-next", summary="Skip Next")
async def skip_next():
    """Skip to the next item"""
    check_speaker_initialized()
    
    result = await speaker_instance.skip_next()
    return result

@app.post("/playback/skip-previous", summary="Skip Previous")
async def skip_previous():
    """Skip to the previous item"""
    check_speaker_initialized()
    
    result = await speaker_instance.skip_previous()
    return result

@app.post("/playback/seek", summary="Seek to Position")
async def seek(request: SeekRequest):
    """Seek to a specified position (in seconds)"""
    check_speaker_initialized()
    
    result = await speaker_instance.seek(request.position)
    return result

@app.post("/playback/preset", summary="Request Playback Preset")
async def request_playback_preset(presetNo: PresetRequest):
    """Request a playback preset"""
    check_speaker_initialized()
    global preset
    
    presets = preset.get("presets", {}).get("presets", {})
    payload = presets.get(str(presetNo.preset), None)
    
    result = await speaker_instance.request_playback_preset(payload, 1)
    return {"status": "success", "result": result}

# Source Control
@app.get("/sources", summary="Get Available Sources")
async def get_sources():
    """Retrieve available sources"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_sources()
    return result

@app.post("/sources/set", summary="Set Source")
async def set_source(request: SourceRequest):
    """Set the playback source"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_source(request.source, request.source_account)
    return result

@app.post("/sources/tv", summary="Switch to TV Source")
async def switch_tv_source():
    """Switch the speaker's source to TV"""
    check_speaker_initialized()
    
    result = await speaker_instance.switch_tv_source()
    return result

@app.post("/sources/bluetooth", summary="Switch to Bluetooth Source")
async def switch_bt_source():
    """Switch the speaker's source to Bluetooth"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_source('BLUETOOTH', '')
    return result

# Audio Settings
@app.get("/audio/{setting}", summary="Get Audio Setting")
async def get_audio_setting(setting: str):
    """Retrieve an audio setting value"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_audio_setting(setting)
    return result

@app.post("/audio/{setting}", summary="Set Audio Setting")
async def set_audio_setting(setting: str, request: AudioSettingRequest):
    """Set an audio setting value"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_audio_setting(setting, request.value)
    return result

@app.get("/audio/mode", summary="Get Audio Mode")
async def get_audio_mode():
    """Retrieve the audio mode"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_audio_mode()
    return result

@app.post("/audio/mode", summary="Set Audio Mode")
async def set_audio_mode(request: AudioModeRequest):
    """Set the audio mode"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_audio_mode(request.mode)
    return {"status": "success", "result": result}

# Bluetooth
@app.get("/bluetooth/status", summary="Get Bluetooth Status")
async def get_bluetooth_status():
    """Retrieve Bluetooth status"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_bluetooth_status()
    return result

# Accessories
@app.get("/accessories", summary="Get Accessories")
async def get_accessories():
    """Retrieve accessories information"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_accessories()
    return result

@app.put("/accessories", summary="Update Accessories")
async def put_accessories(request: AccessoriesRequest):
    """Update accessories settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.put_accessories(request.subs_enabled, request.rears_enabled)
    return {"status": "success", "result": result}

# Battery
@app.get("/battery", summary="Get Battery Status")
async def get_battery_status():
    """Retrieve battery status"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_battery_status()
    return result

# Dual Mono
@app.get("/audio/dual-mono", summary="Get Dual Mono Setting")
async def get_dual_mono_setting():
    """Retrieve the dual mono setting"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_dual_mono_setting()
    return result

@app.post("/audio/dual-mono", summary="Set Dual Mono Setting")
async def set_dual_mono_setting(request: DualMonoRequest):
    """Set the dual mono setting"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_dual_mono_setting(request.value)
    return {"status": "success", "result": result}

# Rebroadcast Latency
@app.get("/audio/rebroadcast-latency", summary="Get Rebroadcast Latency Mode")
async def get_rebroadcast_latency_mode():
    """Retrieve the rebroadcast latency mode"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_rebroadcast_latency_mode()
    return result

@app.post("/audio/rebroadcast-latency", summary="Set Rebroadcast Latency Mode")
async def set_rebroadcast_latency_mode(request: RebroadcastLatencyRequest):
    """Set the rebroadcast latency mode"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_rebroadcast_latency_mode(request.mode)
    return {"status": "success", "result": result}

# Group Management
@app.get("/groups/active", summary="Get Active Groups")
async def get_active_groups():
    """Retrieve active groups"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_active_groups()
    return result

@app.post("/groups/active", summary="Set Active Group")
async def set_active_group(request: ActiveGroupRequest):
    """Set the active group including this device and other products"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_active_group(request.other_product_ids)
    return {"status": "success", "result": result}

@app.put("/groups/active/add", summary="Add to Active Group")
async def add_to_active_group(request: ActiveGroupModifyRequest):
    """Add products to the active group"""
    check_speaker_initialized()
    
    result = await speaker_instance.add_to_active_group(request.active_group_id, request.other_product_ids)
    return {"status": "success", "result": result}

@app.put("/groups/active/remove", summary="Remove from Active Group")
async def remove_from_active_group(request: ActiveGroupModifyRequest):
    """Remove products from the active group"""
    check_speaker_initialized()
    
    result = await speaker_instance.remove_from_active_group(request.active_group_id, request.other_product_ids)
    return {"status": "success", "result": result}

@app.delete("/groups/active", summary="Stop Active Groups")
async def stop_active_groups():
    """Stop all active groups"""
    check_speaker_initialized()
    
    result = await speaker_instance.stop_active_groups()
    return {"status": "success", "result": result}

# CEC Settings
@app.get("/cec", summary="Get CEC Settings")
async def get_cec_settings():
    """Retrieve the CEC settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_cec_settings()
    return result

@app.put("/cec", summary="Set CEC Settings")
async def set_cec_settings(request: CecSettingsRequest):
    """Set the CEC settings"""
    check_speaker_initialized()
    
    result = await speaker_instance.set_cec_settings(request.mode)
    return result

# Network
@app.get("/network/status", summary="Get Network Status")
async def get_network_status():
    """Retrieve the network status"""
    check_speaker_initialized()
    
    result = await speaker_instance.get_network_status()
    return result

# Subscription
@app.put("/subscription", summary="Subscribe to Resources")
async def subscribe(request: SubscribeRequest):
    """Subscribe to a list of resources"""
    check_speaker_initialized()
    
    resources = request.resources if request.resources else None
    result = await speaker_instance.subscribe(resources)
    return result

# Health Check
@app.get("/health", summary="Health Check")
async def health_check():
    """Check if the API and speaker connection are healthy"""
    status = {
        "api_status": "healthy",
        "speaker_connected": speaker_instance is not None,
        "device_id": speaker_instance.get_device_id() if speaker_instance else None
    }
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)