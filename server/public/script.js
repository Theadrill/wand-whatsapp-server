document.addEventListener('DOMContentLoaded', () => {
    const statusBadge = document.getElementById('status-badge');
    const qrContainer = document.getElementById('qr-container');
    const qrImage = document.getElementById('qrcode');
    const instruction = document.getElementById('instruction');
    const onlineMsg = document.getElementById('online-msg');
    const loadingArea = document.getElementById('loading-area');

    // Conecta ao WebSocket do servidor (mesma porta do HTTP)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onopen = () => {
        statusBadge.innerText = 'Conectado ao Servidor';
        statusBadge.style.backgroundColor = '#005c4b';
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Recebido:', message.type);

        if (message.type === 'qrcode') {
            loadingArea.style.display = 'none';
            qrContainer.style.display = 'block';
            qrImage.src = message.data;
            statusBadge.innerText = 'Aguardando Escaneamento';
        }

        if (message.type === 'status' && message.data === 'connected') {
            qrContainer.style.display = 'none';
            loadingArea.style.display = 'none';
            instruction.style.display = 'none';
            onlineMsg.style.display = 'block';
            statusBadge.innerText = 'ONLINE';
            statusBadge.style.backgroundColor = '#00a884';
        }
    };

    ws.onclose = () => {
        statusBadge.innerText = 'Desconectado';
        statusBadge.style.backgroundColor = '#ea0038';
        loadingArea.style.display = 'block';
        loadingArea.querySelector('span').innerText = 'Reconectando ao servidor...';
    };
});
