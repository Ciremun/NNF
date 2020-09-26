// utils

// async function postData(url = '', data = {}) {
//     const response = await fetch(url, {
//       headers: {
//         'Content-Type': 'application/json'
//       },
//       method: 'POST',
//       body: JSON.stringify(data)
//     });
//     return response;
// }

// alert animation @@@ refactor

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

// cart @@@ refactor

async function cartAction(e, act, amount=null) {
    let data = {act: act}
    if (!['submit', 'clear'].includes(act)) {
        if (amount !== null) data.amount = +amount;
        data.productID = +e.dataset.itemid;
    }
    let response = await postData('/cart', data);
    if (response.success) {
        if (act !== 'add') window.location.reload();
        else showAlert('Предмет добавлен в корзину');
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

function login() {
    // @@@ validate login form
    return true;
}

// account share

let shareUsername = document.getElementById('add-shared-username'),
    shareDays     = document.getElementById('add-shared-days'),
    shareHours    = document.getElementById('add-shared-hours'),
    shareMinutes  = document.getElementById('add-shared-minutes'),
    shareSeconds  = document.getElementById('add-shared-seconds');

async function addShared() {
    // @@@ validate addShared form
    return true;
}

// async function shareLogin(e) {
//     login_response = await postData('/login', {target: +e.dataset.userid});
//     await processLoginResponse(login_response);
// }

// async function deleteShared(e) {
//     let response = await postData('/shared', {target: +e.dataset.userid, act: 'del'});
//     if (response.success) window.location.reload();
//     else showAlert(response.message);
// }

// login form @@@ refactor

let loginButton = document.getElementById("showmodal"),
    userfield   = document.getElementById('userfield'),
    passfield   = document.getElementById('passfield');

if (loginButton !== null) loginButton.onclick = () => userfield.focus();
