var typingTimer;
var doneTypingInterval = 100;

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

function showAlert(msg) {
    notify.innerText = msg;
    notify.classList.toggle('alert_animation');
}

async function cartAction(act, amount=null, productID=null) {
    let data = {
        username: window.username,
        act: act
    }
    if (amount !== null) data.amount = Number(amount);
    if (productID !== null) data.productID = Number(productID);
    else data.productID = Number(event.target.dataset.itemid);
    let response = await postData('/cart', data);
    if (response.success) {
        if (act === 'update') window.location.reload();
        else showAlert(`Success: ${act} cart item`);
    } else {
        showAlert(response.message);
    }
}

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

async function deleteShared() {
    let response = await postData('/shared', {target: Number(event.target.dataset.userid), act: 'del'});
    if (response.success) window.location.reload();
    else showAlert(response.message);
}

function setTypingTimer() {
    if (!event.target.value || event.target.value === "0") return;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(cartAction, doneTypingInterval, 'update', event.target.value, event.target.dataset.itemid);
}

function clearTypingTimer() {
    clearTimeout(typingTimer);
}
