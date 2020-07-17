var socket = io();

function logout() {
    socket.emit('logout', {ip: window.ip});
}

socket.on('mainPageRedirect', function() {
    window.location.href = `http://localhost:5001`;
})