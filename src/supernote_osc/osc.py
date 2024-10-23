import asyncio
from osc4py3.as_eventloop import (
    osc_startup,
    osc_process,
    osc_udp_client,
    osc_udp_server,
    osc_terminate,
    osc_method,
    osc_send,
)
from osc4py3 import oscbuildparse as obp
from osc4py3 import oscmethod as osm

import logging
from dataclasses import dataclass

logger = logging.getLogger("osc")

heartbeat_event = asyncio.Event()


@dataclass
class MixerScene:
    name: str
    active: bool


mixer_scene_event = asyncio.Event()
mixer_scenes = {}


@dataclass
class Strip:
    name: str


def handlerfunction(address, data):
    logger.info(f"{address}: {data}")


def handle_heartbeat(_x):
    heartbeat_event.set()
    heartbeat_event.clear()


def handle_mixer_scene(address, name):
    scene_id = int(address.split("/")[2])
    mixer_scenes[scene_id] = MixerScene(name, False)
    mixer_scene_event.set()
    mixer_scene_event.clear()


async def run_osc():
    osc_startup(logger=logger)
    logger.info("Connecting to localhost OSC server")
    osc_udp_client("127.0.0.1", 3819, "daw")
    osc_udp_server("127.0.0.1", 8000, "supernote-osc")
    osc_method("/*", handlerfunction, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)
    osc_method("/heartbeat", handle_heartbeat)
    osc_method(
        "/mixer_scene/*/name",
        handle_mixer_scene,
        argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATAUNPACK,
    )

    strips = (
        1  # audio tracks
        + 2  # midi tracks
        + 4  # audio busses
        + 8  # midi busses
        + 32  # master
    )
    feedback = (
        8  # heartbeat
        + 8192  # select feedback
        + 16384  # OSC /reply instead of #reply
        + 65536  # mixer scene status
    )
    msg = obp.OSCMessage(
        "/set_surface", ",iiiiiiiii", [0, strips, feedback, 0, 0, 0, 8000, 0, 0]
    )
    logger.info("Sending set-surface")
    osc_send(msg, "daw")

    msg = obp.OSCMessage("/strip/expand", ",ii", [1, 1])
    osc_send(msg, "daw")

    try:
        while True:
            osc_process()
            await asyncio.sleep(0.0001)
    except asyncio.CancelledError:
        pass
    osc_terminate()
