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

async function cartAction(act, amount=null, productID=null) {
    let data = {
        username: window.username,
        act: act
    }
    if (!['submit', 'clear'].includes(act)) {
        if (amount !== null) data.amount = Number(amount);
        if (productID !== null) data.productID = Number(productID);
        else data.productID = Number(event.target.dataset.itemid);
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

function setTypingTimer() {
    if (!event.target.value || event.target.value === "0") return;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(cartAction, doneTypingInterval, 'update', event.target.value, event.target.dataset.itemid);
}

function clearTypingTimer() {
    clearTimeout(typingTimer);
}

// login

function loginEnterKey() {
    if (event.key === 'Enter') login();
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

function addSharedEnterKey() {
    if (event.key === 'Enter') {
        let d = getDocumentAccountShareDuration();
        addShared(forever=Object.values(d).every(x => (x === "")), duration=d);
    }
}

function getDocumentAccountShareDuration() {
    return {
        days: document.getElementById('add-shared-days').value,
        hours: document.getElementById('add-shared-hours').value,
        minutes: document.getElementById('add-shared-minutes').value,
        seconds: document.getElementById('add-shared-seconds').value
    };
}

async function addShared(forever=null, duration=null) {
    let username = document.getElementById('add-shared-username').value.toLowerCase();
    if (!username) return showAlert('Error: no username');
    let data = {
        username: username,
        act: 'add'
    };
    if (forever) {
        data.forever = true;
    } else {
        if (!duration) duration = getDocumentAccountShareDuration();
        Object.keys(duration).forEach(x => {
            if (duration[x] === "") duration[x] = 0;
            else duration[x] = Number(duration[x]);
        });
        if (Object.values(duration).reduce((a, b) => a + b) <= 0) return showAlert('Error: invalid account share duration');
        data.duration = duration;
    }
    let response = await postData('/shared', data);
    if (response.success) window.location.reload();
    else showAlert(response.message);
}

async function shareLogin() {
    login_response = await postData('/login', {target: Number(event.target.dataset.userid)});
    await processLoginResponse(login_response);
}

async function deleteShared() {
    let response = await postData('/shared', {target: Number(event.target.dataset.userid), act: 'del'});
    if (response.success) window.location.reload();
    else showAlert(response.message);
}

// login form

let modal = document.getElementById("DivModal"),
    btn = document.getElementById("LoginButton"),
    span = document.getElementsByClassName("CloseModal")[0],
    userfield = document.getElementById('userfield'),
    passfield = document.getElementById('passfield');

if (btn !== null) {
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
}
