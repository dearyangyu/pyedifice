#
# python examples/async.py
#

import os
import sys
# We need this sys.path line for running this example, especially in VSCode debugger.
sys.path.insert(0, os.path.join(sys.path[0], '..'))

import asyncio
from concurrent.futures import ThreadPoolExecutor
import edifice as ed


@ed.component
def AsyncElement(self):

    a, set_a = ed.use_state(0)
    b, set_b = ed.use_state(0)

    async def _on_change1(v:int):
        """
        Test regular async event handlers.
        """
        set_a(v)
        await asyncio.sleep(1)
        set_b(v)


    c, set_c = ed.use_state(0)

    async def async_callback1(v:int):
        set_c(v)

    callback1 = ed.use_async_call(async_callback1)

    async def _on_change2(v:int):
        """
        Test async callbacks from another thread.
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, lambda: callback1(v))


    with ed.View():
        with ed.View(
            style={
                "margin-top": 20,
                "margin-bottom": 20,
                "border-top-width": "1px",
                "border-top-style": "solid",
                "border-top-color": "black",
            },
        ):
            ed.Label(str(a))
            ed.Label(str(b))
            ed.Slider(a, min_value=0, max_value=100, on_change=_on_change1)
        with ed.View(
            style={
                "margin-top": 20,
                "margin-bottom": 20,
                "border-top-width": "1px",
                "border-top-style": "solid",
                "border-top-color": "black",
            },
        ):
            ed.Label(str(c))
            ed.Slider(c, min_value=0, max_value=100, on_change=_on_change2)
if __name__ == "__main__":
    ed.App(ed.Window()(AsyncElement())).start()
