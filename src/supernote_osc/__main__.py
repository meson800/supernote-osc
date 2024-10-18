import asyncio
import uvicorn

import logging
from signal import SIGINT, SIGTERM

from .osc import run_osc

logging.basicConfig(format="%(levelname)s ø %(name)s - %(message)s")
logger = logging.getLogger("osc")
logger.setLevel(logging.INFO)


async def webserver_main():
    config = uvicorn.Config("supernote_osc.router:app", port=8080, log_level="info")
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    await server.shutdown()


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

webserver_task = loop.create_task(webserver_main())
osc_task = loop.create_task(run_osc())

for signal in [SIGINT, SIGTERM]:
    loop.add_signal_handler(signal, webserver_task.cancel)
    loop.add_signal_handler(signal, osc_task.cancel)
loop.run_until_complete(webserver_task)
