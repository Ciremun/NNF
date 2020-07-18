var socket = io();

socket.on('loginSuccess', function(message) {
    let SID = window.getCookie('SID'),
        now = new Date();
    if (SID) socket.emit('clearSID', {SID: SID});
    now.setMonth(now.getMonth() + 3);
    document.cookie = `SID=${message.SID}; expires=${now.toUTCString()}; path=/;`;
    window.location.href = `http://${window.fHost}:${window.fPort}/u/${message.username}`;
})

socket.on('loginFail', function() {
    alert('password did not match');
})

socket.on('unknownSession', function() {
    window.location.reload(true);
})

socket.on('logout', function() {
    document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    window.location.href = `http://${window.fHost}:${window.fPort}`;
})
