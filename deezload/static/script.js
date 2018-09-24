let loadUrl = new URL('load', window.location.href);
loadUrl.protocol = loadUrl.protocol.replace('http', 'ws');
let socket = new WebSocket(loadUrl.href);
let stopLoad = false;
let errorIsVisible = false;

let mainWin = document.getElementById('main-win');
let loadWin = document.getElementById('load-win');

let mainForm = document.getElementById('main-form');
let progress = document.getElementById('progress');
let logs = document.getElementById('logs');

let stopButton = document.getElementById('stop-btn');
let finishButton = document.getElementById('finish-btn');

function setProgress(proc) {
    proc = Math.round(proc);
    proc = `${proc}%`;
    progress.style.width = proc;
    progress.textContent = proc;
}

function addLog(cls, msg, left = true) {
    let lastMaxScroll = logs.scrollHeight - logs.offsetHeight;
    let side = left ? 'left' : 'right';
    logs.innerHTML += `<div class="${cls} ${side}">${msg}</div>`;
    // scroll more if at the bottom
    if (logs.scrollTop === lastMaxScroll) {
        logs.scrollTop = logs.scrollHeight;
    }
}

function removeError() {
    if (errorIsVisible) {
        mainWin.removeChild(mainWin.lastChild);
        errorIsVisible = false;
    }
}

stopButton.onclick = function () {
    addLog('stop-msg', 'wait till one more audio file loads before stop', true);
    stopLoad = true;
};

finishButton.onclick = function () {
    mainWin.style.display = 'block';
    loadWin.style.display = 'none';
    finishButton.style.display = 'none';
    stopButton.style.display = 'block';
    logs.innerHTML = '';
    stopLoad = false;
    setProgress(0);
};

mainForm.onsubmit = function (event) {
    event.preventDefault();
    removeError();
    let formData = new FormData(mainForm);
    let data = {
        'type': 'start',
        'url': formData.get('url'),
        'index': parseInt(formData.get('index').toString()),
        'limit': parseInt(formData.get('limit').toString()),
        'format': formData.get('format'),
        'tree': !!formData.get('tree'),
    };
    socket.send(JSON.stringify(data));
};

socket.onmessage = function (event) {
    let data = JSON.parse(event.data);

    if (data.type === 'status') {
        if (data.status === 'starting') {
            addLog('start-msg', data.message, true);
        }
        else if (data.status === 'skipped') {
            addLog('warn-msg', data.message, false);
        }
        else {
            addLog('info-msg', data.message, false);
        }

        let proc = (data.index + data.prog) / data.size * 100;
        setProgress(proc);

    } else if (data.type === 'error') {
        removeError();
        errorIsVisible = true;
        let error = document.createElement('div');
        error.classList.add('error');
        error.innerText = data.message;
        mainWin.appendChild(error);

    } else if (data.type === 'start') {
        mainWin.style.display = 'none';
        loadWin.style.display = 'block';

    } else if (data.type === 'complete') {
        finishButton.style.display = 'block';
        stopButton.style.display = 'none';

        let msg = `<div>loaded: ${data.loaded}</div>
                       <div>existed: ${data.existed}</div>
                       <div>skipped: ${data.skipped}</div>`;
        addLog('final-msg', msg);
    }
    let respType = 'ok';
    if (stopLoad) {
        respType = 'stop';
    }
    socket.send(JSON.stringify({
        'type': respType,
    }));
};
