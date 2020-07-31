
function loginEnterKey() {
    if (event.key === 'Enter') login();
}

async function login() {
    login_response = await postData('/login', {displayname: userfield.value, password: passfield.value});
    if (login_response.success) {
        let SID = getCookie('SID'),
            now = new Date();
        if (SID) postData('/logout', {SID: SID});
        now.setMonth(now.getMonth() + 1);
        document.cookie = `SID=${login_response.SID}; expires=${now.toUTCString()}; path=/;`;
        window.location.href = `${location.protocol}//${window.location.host}/menu`;
    } else {
        alert(login_response.message);
        passfield.value = "";
    }
}

async function logout() {
    let response = await postData('/logout', {SID: getCookie('SID')});
    if (response.success) {
        document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = `${location.protocol}//${window.location.host}`;
    } else {
        window.location.reload(true);
    }
}

let modal = document.getElementById("DivModal"),
    btn = document.getElementById("LoginButton"),
    span = document.getElementsByClassName("CloseModal")[0],
    userfield = document.getElementById('userfield'),
    passfield = document.getElementById('passfield');

btn.onclick = function() {
    modal.style.display = "block";
    userfield.focus();
}

span.onclick = function() {
    modal.style.display = "none";
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
