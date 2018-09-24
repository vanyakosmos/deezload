import json
import logging
import os

from sanic import Sanic
from sanic.request import Request
from sanic.response import html
from sanic.websocket import WebSocketCommonProtocol as WebSocket

from deezload.base import AppException, LoadStatus, Loader
from deezload.settings import HOME_DIR, ROOT_PATH


app = Sanic()
app.static('/static', os.path.join(ROOT_PATH, 'static'))
logger = logging.getLogger(__name__)


async def recv(ws: WebSocket) -> dict:
    data = await ws.recv()
    data = json.loads(data)
    return data


async def send_message(ws: WebSocket, type_: str, message='ok', kw=None):
    kw = kw or {}
    await ws.send(json.dumps({
        'type': type_,
        'message': message,
        **kw,
    }))


async def load_cycle(ws: WebSocket):
    data = await recv(ws)
    if data['type'] != 'start':
        return

    try:
        loader = Loader(
            urls=data.get('url'),
            output_dir=HOME_DIR,
            index=data.get('index'),
            limit=data.get('limit'),
            format=data.get('format'),
            tree=data.get('tree'),
            playlist_name=data.get('playlist') or None,
        )
        await send_message(ws, 'start')

    except AppException as e:
        logger.warning(e)
        await send_message(ws, 'error', str(e))
        return

    except Exception as e:
        logger.exception(e)
        return

    # share playlist name
    name = loader.playlists[0].name
    await send_message(ws, 'playlist_name', name)

    should_stop = False
    loaded, existed, skipped = 0, 0, 0
    for status, track, i, prog in loader.load_gen():
        if status == LoadStatus.STARTING:
            message = track.short_name
        elif status == LoadStatus.SEARCHING:
            message = "searching for video..."
        elif status == LoadStatus.LOADING:
            message = "loading audio..."
        elif status == LoadStatus.MOVING:
            message = f"moving file..."
        elif status == LoadStatus.RESTORING_META:
            message = "restoring meta data..."

        elif status == LoadStatus.SKIPPED:
            message = "wasn't able to find video for track"
            skipped += 1
        elif status == LoadStatus.EXISTED:
            message = f"track already exists at {track.path}"
            existed += 1
        elif status == LoadStatus.FINISHED:
            loaded += 1
            message = "done!"
        else:
            message = None

        if message:
            await send_message(ws, 'status', message, {
                'status': str(status),
                'index': i,
                'prog': prog,
                'size': len(loader)
            })
            resp = await recv(ws)
            if resp['type'] == 'stop':
                should_stop = True

        if should_stop and status in LoadStatus.finite_states():
            break

    await send_message(ws, 'complete', kw={
        'loaded': loaded,
        'existed': existed,
        'skipped': skipped,
    })


@app.websocket('/load')
async def load(_: Request, ws: WebSocket):
    while True:
        logger.info('♻️ NEW CYCLE ♻️')
        await load_cycle(ws)


@app.route("/")
async def index(_):
    return html(open(os.path.join(ROOT_PATH, 'index.html')).read())


def start_server(debug=False):
    app.run(host="0.0.0.0", port=8000, debug=debug)
