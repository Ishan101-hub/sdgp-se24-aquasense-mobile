# run.py
# AquaSense — Windows-safe startup script.
#
# WHY this file exists:
#   aiomqtt uses loop.add_reader() / loop.add_writer() which only work on
#   SelectorEventLoop. Windows Python 3.8+ defaults to ProactorEventLoop.
#
# WHY the previous fix didn't work:
#   asyncio.set_event_loop_policy() sets the POLICY, but uvicorn.run() calls
#   its own loop setup internally and overrides it, ending up with
#   ProactorEventLoop regardless of what the policy says.
#
# THIS fix:
#   Use asyncio.run() to create the event loop ourselves FIRST (using the
#   SelectorEventLoop policy), then pass control to uvicorn.Server.serve()
#   which runs INSIDE our loop. Nothing can override it at this point.
#
# Usage:  python run.py   (always use this, never `uvicorn main:app`)

import asyncio
import sys


# Step 1 — set policy before ANYTHING else runs
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✅ Windows: SelectorEventLoop policy applied")

# Step 2 — import uvicorn AFTER setting the policy
import uvicorn


async def _serve() -> None:
    """Run uvicorn inside the already-created SelectorEventLoop."""
    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # loop="none" tells uvicorn: don't touch the event loop,
        # we already have one (the SelectorEventLoop from asyncio.run below).
        loop="none",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    # asyncio.run() creates a new event loop using the policy we set above.
    # On Windows that is now SelectorEventLoop — aiomqtt works correctly.
    asyncio.run(_serve())