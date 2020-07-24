
function loginEnterKey() {
    if (event.key === 'Enter') login();
}

async function login() {

    let usernameField = document.getElementById('userfield'),
        passwordField = document.getElementById('passfield'),
        username = usernameField.value,
        password = passwordField.value;

    login_response = await postData('/login', {username: username.toLowerCase(), displayname: username, password: password});
    
    if (login_response.success) {
        let SID = window.getCookie('SID'),
            now = new Date();
        if (SID) postData('/logout', {SID: SID});
        now.setMonth(now.getMonth() + 1);
        document.cookie = `SID=${login_response.SID}; expires=${now.toUTCString()}; path=/;`;
        window.location.href = `${location.protocol}//${window.location.host}/menu`;
    } else {
        alert(login_response.message);
        passwordField.value = "";
    }
}
