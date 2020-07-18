
function logout() {
    socket.emit('logout', {SID: window.getCookie('SID')});
}
