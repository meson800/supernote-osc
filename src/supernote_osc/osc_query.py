"""
Handles OSC querying using special parsing functions
that abstract the network traffic.

In general, to send a query message, you need to hold an asyncio lock
that sets the type of response you are expecting. You need to pass
a function that parses response messages and does something with them,
and returns true when parsing is complete.
"""

from osc4py3 import oscbuildparse as obp
from osc4py3.as_eventloop import (
    osc_send,
)
from asyncio import Lock, Event

reply_lock = Lock()
reply_done = Event()
reply_state = {"parse": lambda _a, _d: True}


def handle_reply(address, data):
    if reply_state["parse"](address, data):
        # we're done parsing, signal the event and reset
        reply_done.set()


async def query(message: obp.OSCMessage, parser):
    """
    Sends a query to the DAW and processes messages
    """
    async with reply_lock:
        reply_done.clear()
        reply_state["parse"] = parser
        osc_send(message, "daw")
        await reply_done.wait()
