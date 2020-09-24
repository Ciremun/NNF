// utils

function getCookie(name) {
    let matches = document.cookie.match(new RegExp(
      "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
    ));
    return matches ? decodeURIComponent(matches[1]) : undefined;
}

async function postData(url = '', data = {}) {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'POST',
      body: JSON.stringify(data)
    });
    return response.json();
}

// alert animation

function showAlert(msg) {
    notify.innerText = msg;
    notify.classList.toggle('alert_animation');
}

let notify = document.getElementById("alert");

notify.addEventListener('animationstart', () => {
    notify.style.opacity = 1;
});

notify.addEventListener('animationend', () => {
    notify.style.opacity = 0;
});

notify.addEventListener('animationcancel', () => {
    notify.style.opacity = 0;
    notify.classList.toggle('alert_animation');
});

// cart

async function cartAction(e, act, amount=null) {
    let data = {
        username: window.username,
        act: act
    }
    if (!['submit', 'clear'].includes(act)) {
        if (amount !== null) data.amount = +amount;
        data.productID = +e.dataset.itemid;
    }
    let response = await postData('/cart', data);
    if (response.success) {
        if (act !== 'add') window.location.reload();
        else showAlert(`Success: add cart item`);
    } else {
        showAlert(response.message);
    }
}

// typingTimer

let typingTimer;
let doneTypingInterval = 100;

function setCartAmountTypingTimer(e) {
    if (!e.value || e.value === "0") return;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(cartAction, doneTypingInterval, e, 'update', e.value);
}

function clearTypingTimer() {
    clearTimeout(typingTimer);
}

// login

function loginEnterKey(e) {
    if (e.key === 'Enter') login();
}

async function processLoginResponse(login_response) {
    if (login_response.success) {
        let SID = getCookie('SID'),
            now = new Date();
        if (SID) postData('/logout', {SID: SID});
        now.setMonth(now.getMonth() + 1);
        document.cookie = `SID=${login_response.SID}; expires=${now.toUTCString()}; path=/;`;
        window.location.reload();
    } else {
        showAlert(login_response.message);
    }
}

async function login() {
    login_response = await postData('/login', {displayname: userfield.value, password: passfield.value});
    await processLoginResponse(login_response);
    passfield.value = "";
}

async function logout() {
    let response = await postData('/logout', {SID: getCookie('SID')});
    if (response.success) document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    window.location.reload();
}

// account share

let shareDays    = document.getElementById('add-shared-days'),
    shareHours   = document.getElementById('add-shared-hours'),
    shareMinutes = document.getElementById('add-shared-minutes'),
    shareSeconds = document.getElementById('add-shared-seconds');

async function addShared() {
    let username = document.getElementById('add-shared-username').value.toLowerCase();
    if (!username) return showAlert('Error: no username');
    let data = {
        username: username,
        act: 'add'
    };
    if ([shareDays.value, shareHours.value, shareMinutes.value, shareSeconds.value].every(x => (x === ""))) {
        data.forever = true;
    } else {
        let duration = [shareDays.value, shareHours.value, 
                        shareMinutes.value, shareSeconds.value];
        duration = duration.map(x => x === "" ? 0 : +x);
        console.log(duration);
        console.log(duration.reduce((a, b) => a + b) <= 0);
        if (duration.reduce((a, b) => a + b) <= 0) return showAlert('Error: invalid account share duration');
        data.days    = duration[0];
        data.hours   = duration[1];
        data.minutes = duration[2];
        data.seconds = duration[3];
    }
    let response = await postData('/shared', data);
    if (response.success) window.location.reload();
    else showAlert(response.message);
}

async function shareLogin(e) {
    login_response = await postData('/login', {target: +e.dataset.userid});
    await processLoginResponse(login_response);
}

async function deleteShared(e) {
    let response = await postData('/shared', {target: +e.dataset.userid, act: 'del'});
    if (response.success) window.location.reload();
    else showAlert(response.message);
}

// login form

let loginForm   = document.getElementById("DivModal"),
    loginButton = document.getElementById("LoginButton"),
    closeModal  = document.getElementsByClassName("CloseModal")[0],
    userfield   = document.getElementById('userfield'),
    passfield   = document.getElementById('passfield');

if (loginButton !== null) {
    loginButton.onclick = function() {
        loginForm.style.display = "block";
        userfield.focus();
    }

    closeModal.onclick = function() {
        loginForm.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == loginForm) {
            loginForm.style.display = "none";
        }
    }
}
