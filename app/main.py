from typing import Union, Annotated
from fastapi import FastAPI, Request, Query
from contextlib import asynccontextmanager
import pybose, json, asyncio, sys, os, logging
from pybose import BoseAuth, BoseSpeaker
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logger = logging.getLogger('uvicorn.error')

# config
VOLUME_STEP = os.getenv('BOSE_VOLUME_STEP', 5)

try: 
    description = Path('../README.md').read_text()
except:
    description = ''

# set up Bose connector
bose_auth = BoseAuth()
control_token = bose_auth.getControlToken(os.getenv('BOSE_USERNAME'), os.getenv('BOSE_PASSWORD'))
if control_token: 
    logger.info("Bose auth success")
else:
    logger.error("Bose auth error")

bose = BoseSpeaker(bose_auth=bose_auth, device_id=os.getenv('BOSE_DEVICE_ID'), host=os.getenv('BOSE_HOST'))
bose.attach_receiver(lambda data: logger.info(f"Received unsolicited message: {json.dumps(data, indent=4)}"))

async def connect():
    return await bose.connect()

@asynccontextmanager
async def lifespan(app: FastAPI):
    bose = await connect()  
    logger.info(f"Bose connector successfull")
    yield

app = FastAPI(
    title="Bose REST API",
    description=description,
    version="0.0.1",
    contact={
        "name": "Simon Aebersold",
        "url": "https://github.com/aebersold",
        "email": "s.aebersold@gmail.com",
    },
    lifespan=lifespan)

@app.get("/")
async def root():
    res = []
    for funcname in ['get_system_info', 'get_product_settings', 'get_network_status', 'get_accessories', 'get_audio_mode']:
        res.append(await getattr(bose, funcname)())
    return res

@app.get("/status")
async def status():
    res = []
    for funcname in ['get_power_state', 'get_now_playing', 'get_bluetooth_status']:
        res.append(await getattr(bose, funcname)())
    return res

@app.get("/sources")
async def sources():
    response = await bose.get_sources()
    return response

@app.get("/set_state")
async def state(set: bool = False):
    await bose.set_power_state(set)
    response = await bose.get_power_state()
    return response

@app.get("/volume")
async def get_volume():
    response = await bose.get_audio_volume()
    return response

@app.get("/volume_set_to")
async def set_volume(volume: int):
    response = await bose.set_audio_volume(max(0, volume))
    return response

@app.get("/volume_up")
async def volume_up():
    cur = await bose.get_audio_volume()
    response = await bose.set_audio_volume(min(100, cur['value'] + VOLUME_STEP))
    return response

@app.get("/volume_down")
async def volume_down():
    cur = await bose.get_audio_volume()
    response = await bose.set_audio_volume(max(0, cur['value'] - VOLUME_STEP))
    return response

@app.get("/source_set")
async def source_set(source: str, sourceAccount: str):
    response = await bose.set_source()
    return response

@app.get("/tv")
async def switch_to_tv():
    response = await bose.switch_tv_source()
    return response

@app.get("/bluetooth")
async def switch_to_bt():
    response = await bose.set_source('BLUETOOTH', '')
    return response

@app.get("/play")
async def play():
    response = await bose.play()
    return response

@app.get("/pause")
async def pause():
    response = await bose.pause()
    return response

@app.get("/next")
async def next():
    response = await bose.skip_next()
    return response

@app.get("/previous")
async def previous():
    response = await bose.skip_previous()
    return response