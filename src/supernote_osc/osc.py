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

logger = logging.getLogger("osc")


def handlerfunction(address, data):
    logger.info(f"{address}: {data}")


async def run_osc():
    osc_startup(logger=logger)
    logger.info("Connecting to localhost OSC server")
    osc_udp_client("127.0.0.1", 3819, "daw")
    osc_udp_server("127.0.0.1", 8000, "supernote-osc")
    osc_method("/*", handlerfunction, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)

    msg = obp.OSCMessage(
        "/set_surface", ",iiiiiiiii", [0, 31, 65544, 0, 0, 0, 8000, 0, 0]
    )
    logger.info("Sending set-surface")
    osc_send(msg, "daw")

    try:
        while True:
            osc_process()
            await asyncio.sleep(0.0001)
    except asyncio.CancelledError:
        pass
    osc_terminate()
