
var socket = io();
socket.on('connect', function() {
    socket.emit('connect_', {data: 'socketio connected'});
});

function loginEnterKey() {
    if(event.key === 'Enter') login();
}

function login() {
    let usernameField = document.getElementById('userfield'),
        passwordField = document.getElementById('passfield'),
        username = usernameField.value,
        password = passwordField.value;

    if (!username || !password) {
        alert('enter username and password');
        return;
    }

    [username, password].forEach(x => {
        for (var i = 0; i < x.length; i++) {
            code = x.charCodeAt(i);
            if(code == 32)
            {
                alert('no spaces please');
                return;
            }
            if(48 <= code && code <= 57) continue;
            if(65 <= code && code <= 90) continue;
            if(97 <= code && code <= 122) continue;
            alert('only english characters and numbers');
            return;
          }
    });

    socket.emit('register', {username: username, password: password});

    usernameField.value = "";
    passwordField.value = "";
}
