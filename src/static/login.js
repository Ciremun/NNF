
var socket = io();

socket.on('loginSuccess', function(message) {
    var now = new Date();
    now.setMonth(now.getMinutes() + 1);
    document.cookie = `SID=${message.SID}; expires=${now.toUTCString()}; path=/;`;
    window.location.href = `http://${window.fHost}:${window.fPort}/u/${message.username}`;
})

socket.on('loginFail', function() {
    alert('password did not match');
})

function loginEnterKey() {
    if(event.key === 'Enter') login();
}

function login() {

    let SID = window.getCookie('SID');
    if (SID) socket.emit('clearSID', {SID: SID});

    let usernameField = document.getElementById('userfield'),
        passwordField = document.getElementById('passfield'),
        username = usernameField.value,
        password = passwordField.value;

    if (!username || !password) {
        alert('enter username and password');
        return;
    }

    let error = false;

    [username, password].forEach(x => {
        for (var i = 0; i < x.length; i++) {
            code = x.charCodeAt(i);
            if(code == 32)
            {
                alert('no spaces please');
                error = true;
                break;
            }
            if(48 <= code && code <= 57) continue;
            if(65 <= code && code <= 90) continue;
            if(97 <= code && code <= 122) continue;
            alert('only english characters and numbers');
            error = true;
            break;
          }
    });

    if (error) return;

    socket.emit('login', {username: username.toLowerCase(), displayname: username, password: password});

    passwordField.value = "";
}
