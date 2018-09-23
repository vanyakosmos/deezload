import json
import logging

from sanic import Sanic
from sanic.request import Request
from sanic.response import html
from sanic.websocket import WebSocketCommonProtocol as WebSocket

from deezload.base import AppException, LoadStatus, Loader
from deezload.settings import DEBUG


app = Sanic()
logger = logging.getLogger(__name__)


async def load_cycle(ws: WebSocket):
    while True:
        data = await ws.recv()
        data = json.loads(data)

        try:
            loader = Loader(
                urls=data.get('url'),
                output_dir='../output',
                index=data.get('index'),
                limit=data.get('limit'),
                format=data.get('format'),
                tree=data.get('tree'),
            )
            break
        except AppException as e:
            logger.warning(e)
            await ws.send(json.dumps({
                'type': 'error',
                'message': str(e),
            }))
            await ws.recv()
        except Exception as e:
            logger.exception(e)
            return

    await ws.send(json.dumps({
        'type': 'start',
        'message': 'ok',
    }))
    await ws.recv()

    for status, track, i, prog in loader.load_gen():
        if status == LoadStatus.STARTING:
            message = track.short_name
        elif status == LoadStatus.SEARCHING:
            message = "searching for video..."
        elif status == LoadStatus.LOADING:
            message = "loading audio..."
        elif status == LoadStatus.MOVING:
            message = "moving file..."
        elif status == LoadStatus.RESTORING_META:
            message = "restoring file meta data..."

        elif status == LoadStatus.SKIPPED:
            message = "⚠️ wasn't able to find track"
        elif status == LoadStatus.EXISTED:
            message = f"track already exists at {track.path}"
        elif status == LoadStatus.FINISHED:
            message = "done!"
        else:
            message = None
        if message:
            await ws.send(json.dumps({
                'type': 'status',
                'status': str(status),
                'message': message,
                'index': i,
                'prog': prog,
                'size': len(loader)
            }))
            resp = await ws.recv()
            if resp == 'stop':
                break
    await ws.send(json.dumps({
        'type': 'complete',
        'message': 'ok',
    }))
    await ws.recv()


@app.websocket('/load')
async def load(_: Request, ws: WebSocket):
    while True:
        print('NEW CYCLE')
        await load_cycle(ws)


@app.route("/")
async def index(_):
    return html(open('index.html').read())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=DEBUG)
