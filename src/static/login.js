
function loginEnterKey() {
    if(event.key === 'Enter') login();
}

async function login() {

    let usernameField = document.getElementById('userfield'),
        passwordField = document.getElementById('passfield'),
        username = usernameField.value,
        password = passwordField.value;

    if (!username || !password) {
        alert('enter username and password');
        return;
    }

    if (username.length > 25 || password.length > 25)
    {
        alert('max username/password length = 25!');
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
                return;
            }
            if(48 <= code && code <= 57) continue;
            if(65 <= code && code <= 90) continue;
            if(97 <= code && code <= 122) continue;
            alert('only english characters and numbers');
            error = true;
            return;
          }
    });

    if (error) return;

    login_response = await postData('/login', {username: username.toLowerCase(), displayname: username, password: password});
    
    if (login_response.status === 200) {
        let SID = window.getCookie('SID'),
        now = new Date();
        if (SID) await postData('/api/clearSID_onlogin', {SID: SID});
        now.setMonth(now.getMonth() + 1);
        document.cookie = `SID=${login_response.SID}; expires=${now.toUTCString()}; path=/;`;
        window.location.href = `${location.protocol}//${window.location.host}/u/${login_response.username}`;
    } else {
        alert('password did not match');
        passwordField.value = "";
    }
}
