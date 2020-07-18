
var socket = io();

function logout() {
    socket.emit('logout', {SID: window.getCookie('SID')});
}

socket.on('logout', function() {
    document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    window.location.href = `http://${window.fHost}:${window.fPort}`;
})
