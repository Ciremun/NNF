// utils

async function postData(url, data = {}) {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'POST',
      body: JSON.stringify(data)
    });
    return response.json();
}

function showAlert(message) {
    let alerts = document.getElementsByClassName('alert');
    if (alerts.length !== 0) 
        for (item of alerts)
            item.remove();
    let outer_div = document.createElement('div'),
        inner_div = document.createElement('div');
    outer_div.classList.add('alert');
    inner_div.classList.add('alert_content');
    inner_div.innerText = message;
    outer_div.appendChild(inner_div);
    document.body.appendChild(outer_div);
}

// cart @@@ refactor

async function cartAction(e, act=null, amount=null) {
    if (act === null) act = e.value;
    let data = {act: act};
    if (amount !== null) data.amount = +amount;
    if (!['cartsbm', 'cartcl'].includes(act)) data.productID = +e.dataset.itemid;
    let response = await postData('/cart', data);
    if (!['cartadd', 'fav'].includes(act)) window.location.reload();
    if (response.message) showAlert(response.message);
}

// typingTimer

let typingTimer;
let doneTypingInterval = 100;

function setCartAmountTypingTimer(e) {
    if (!e.value || e.value === "0") return;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(cartAction, doneTypingInterval, e, 'cartupd', e.value);
}

function clearTypingTimer() {
    clearTimeout(typingTimer);
}

// login

let loginButton = document.getElementById("showmodal"),
    userfield   = document.getElementById('userfield'),
    passfield   = document.getElementById('passfield');

function login() {
    // @@@ validate login form
    return true;
}

if (loginButton !== null) loginButton.onclick = () => userfield.focus();

// account share

let shareUsername = document.getElementById('add-shared-username'),
    shareDays     = document.getElementById('add-shared-days'),
    shareHours    = document.getElementById('add-shared-hours'),
    shareMinutes  = document.getElementById('add-shared-minutes'),
    shareSeconds  = document.getElementById('add-shared-seconds');

function addShared() {
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
