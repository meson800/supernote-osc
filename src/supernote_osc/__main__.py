import asyncio
import uvicorn

from signal import SIGINT, SIGTERM


async def webserver_main():
    config = uvicorn.Config("supernote_osc.router:app", port=8080, log_level="info")
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        await server.shutdown()


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

webserver_task = loop.create_task(webserver_main())

for signal in [SIGINT, SIGTERM]:
    loop.add_signal_handler(signal, webserver_task.cancel)
loop.run_until_complete(webserver_task)
