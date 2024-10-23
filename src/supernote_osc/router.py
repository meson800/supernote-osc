from fastapi import FastAPI

from .osc import heartbeat_event, mixer_scene_event, mixer_scenes, osc_send, obp

app = FastAPI()


@app.get("/")
async def hello_world():
    return {"Hello": "World"}


@app.get("/heartbeat")
async def heartbeat():
    # only mildly cursed
    if "last" not in heartbeat.__dict__:
        heartbeat.last = 0

    await heartbeat_event.wait()
    heartbeat.last = 1 if heartbeat.last == 0 else 0
    return heartbeat.last


@app.get("/mixer_scene")
async def get_mixer_scene_data():
    await mixer_scene_event.wait()
    return mixer_scenes


@app.post("/mixer_scene/{id}")
async def set_mixer_scene(id: int):
    for k_id in mixer_scenes.keys():
        mixer_scenes[k_id].active = k_id == id
    msg = obp.OSCMessage("/access_action", ",s", [f"Mixer/recall-mixer-scene-{id}"])
    osc_send(msg, "daw")
    return mixer_scenes


@app.post("/select/{id}")
async def expand_strip(id: int):
    msg = obp.OSCMessage("/select/expand", ",ii", [id, 1])
    osc_send(msg, "daw")
    return


@app.post("/select/plugin/{delta}")
async def shift_selected_plugin(delta: int):
    msg = obp.OSCMessage("/select/plugin", ",i", [delta])
    osc_send(msg, "daw")
    return


# If we receive strip/list, we need to ping it again
@app.get("/striplist")
async def send_strip_list():
    msg = obp.OSCMessage("/strip/list", ",", [])
    osc_send(msg, "daw")
    return


@app.get("/strip/{id}/plugins")
async def get_strip_plugins(id: int):
    msg = obp.OSCMessage("/strip/plugin/list", ",i", [id])
    osc_send(msg, "daw")
    return


@app.get("/strip/{ssid}/plugins/{piid}")
async def get_strip_plugin_params(ssid: int, piid):
    msg = obp.OSCMessage("/strip/plugin/descriptor", ",ii", [ssid, piid])
    osc_send(msg, "daw")
    return


@app.get("/longpoll/{osc_path:path}")
async def longpoll(osc_path: str):
    print(osc_path)
