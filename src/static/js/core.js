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

function between(x, min, max) {
    return x >= min && x <= max;
}

// cart

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
    if (isNaN(e.value) || +e.value <= 0) return;
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

async function login() {
    let pair = [userfield.value, passfield.value];
    for (str of pair)
        for (letter of str) {
            let code = letter.charCodeAt();
            if (!between(code, 48, 57) && !between(code, 65, 90) && !between(code, 97, 122))
                return showAlert('Ошибка: только английские символы и числа');
        }
    let response = await postData('/login', {displayname: pair[0], password: pair[1]});
    if (response.success) window.location.reload();
    if (response.message) showAlert(response.message);
}

if (loginButton !== null) loginButton.onclick = () => userfield.focus();

// account share

function addShared() {
    let duration = [
        document.getElementById('add-shared-days').value,
        document.getElementById('add-shared-hours').value,
        document.getElementById('add-shared-minutes').value,
        document.getElementById('add-shared-seconds').value
    ];
    if (duration.every(x => x === ""))
        return true;
    duration = duration.map(x => +x);
    if (duration.some(x => isNaN(x)) || duration.reduce((a, b) => a + b, 0) <= 0) {
        showAlert('Ошибка: неверная длительность раздачи');
        return false;
    }
    return true;
}
