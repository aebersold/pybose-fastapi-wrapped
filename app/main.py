from typing import Union
from fastapi import FastAPI, Request

import pybose, json, asyncio, sys, os
from pybose import BoseAuth, BoseSpeaker
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

async def connect():
    bose_auth = BoseAuth()
    control_token = bose_auth.getControlToken(os.getenv('USERNAME'), os.getenv('PASSWORD'))

    print(json.dumps(control_token, indent=4))

    bose = BoseSpeaker(bose_auth=bose_auth, device_id=os.getenv('DEVICE_ID'), host=os.getenv('HOST'))
    bose.attach_receiver(lambda data: print(f"Received unsolicited message: {json.dumps(data, indent=4)}"))
    await bose.connect()
    return bose


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    bose = await connect()
    
    request.state.bose = bose
    response = await call_next(request)
    # await bose.disconnect() # bugs out

    return response


@app.get("/")
async def read_root(request: Request):
    response = await request.state.bose.get_system_info()
    return response

@app.get("/tv")
async def read_tv(request: Request):
    response = await request.state.bose.switch_tv_source()
    return response

@app.get("/play")
async def read_play(request: Request):
    response = await request.state.bose.play()
    return response

@app.get("/pause")
async def read_pause(request: Request):
    response = await request.state.bose.pause()
    return response

@app.get("/next")
async def read_next(request: Request):
    response = await request.state.bose.skip_next()
    return response

@app.get("/previous")
async def read_previous(request: Request):
    response = await request.state.bose.skip_previous()
    return response