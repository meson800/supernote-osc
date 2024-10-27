import asyncio
import itertools
from typing import Dict
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

from .osc_query import handle_reply, query
from . import ardour

logger = logging.getLogger("osc")

heartbeat_event = asyncio.Event()


@dataclass
class MixerScene:
    name: str
    active: bool


mixer_scene_event = asyncio.Event()
mixer_scenes = {}


strips: Dict[int, ardour.Strip] = {}


def parse_strip_metadata(data) -> ardour.Strip:
    strip_type = ardour.StripType(data[0])
    if (
        strip_type == ardour.StripType.AudioTrack
        or strip_type == ardour.StripType.MidiTrack
    ):
        assert len(data) == 8
    else:
        assert len(data) == 7

    return ardour.Strip(
        strip_type=ardour.StripType(data[0]),
        name=data[1],
        n_inputs=data[2],
        n_outputs=data[3],
        muted=True if data[4] == 1 else False,
        soloed=True if data[5] == 1 else False,
        ssid=data[6],
        record_enabled=True if len(data) == 8 and data[7] == 1 else False,
        plugins={},
    )


def handle_strip_list_reply(_address, data):
    if data[0] == "end_route_list":
        return True
    strip = parse_strip_metadata(data)
    strips[strip.ssid] = strip


def handle_plugin_list(address, data):
    """Parse /strip/plugin/list response data"""
    assert address == "/strip/plugin/list"
    assert len(data) % 3 == 1

    ssid = data[0]
    for piid, name, enabled in itertools.batched(data[1:], 3):
        strips[ssid].plugins[piid] = ardour.StripPlugin(piid, name, (enabled == 1), {})
    return True


def handle_plugin_parameters(address, data):
    """
    Parse /strip/plugin/descriptor response data
    The last parameter is followed by /strip/plugin/descriptor_end
    """
    if address == "/strip/plugin/descriptor_end":
        return True
    assert address == "/strip/plugin/descriptor"
    ssid, piid, param_id = data[0:3]

    strips[ssid].plugins[piid].parameters[param_id] = ardour.PluginParameter(
        param_id=param_id,
        name=data[3],
        options=ardour.ParameterOption(data[4]),
        dtype=data[5],
        min_val=data[6],
        max_val=data[7],
        scale_points=[
            ardour.ScalePoint(t[1], t[0]) for t in itertools.batched(data[8:-1], 2)
        ],
        value=data[-1],
    )


async def update_strips() -> None:
    """
    Refetch all strip information from Ardour
    """
    msg = obp.OSCMessage("/strip/list", ",", [])
    await query(msg, handle_strip_list_reply)


async def update_strip_plugins(ssid: int) -> None:
    """
    Refetch all plugin details (+ parameters) for a given strip
    """
    # refresh strips first, in case it changed from under us
    await update_strips()
    msg = obp.OSCMessage("/strip/plugin/list", ",i", [ssid])
    await query(msg, handle_plugin_list)
    # save strip ids because these calls modify the underlying lists
    piids = list(strips[ssid].plugins.keys())
    for piid in piids:
        msg = obp.OSCMessage("/strip/plugin/descriptor", ",ii", [ssid, piid])
        await query(msg, handle_plugin_parameters)


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
    osc_method("/reply", handle_reply, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)
    osc_method(
        "/strip/plugin/list",
        handle_reply,
        argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA,
    )
    osc_method(
        "/strip/plugin/descriptor",
        handle_reply,
        argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA,
    )
    osc_method(
        "/strip/plugin/descriptor_end",
        handle_reply,
        argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA,
    )
    osc_method("/reply", handle_reply, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)
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
        0
        #    8  # heartbeat
        #    + 8192  # select feedback
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
