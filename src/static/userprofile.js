var socket = io();

function logout() {
    socket.emit('logout', {ip: window.ip});
}

socket.on('mainPageRedirect', function(message) {
    window.location.href = `http://${message.host}:${message.port}`;
})