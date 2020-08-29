const sleep = (ms) => {
    return new Promise(resolve => setTimeout(resolve, ms))
}

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

async function addToCart() {
    let response = await postData('/cart', {productID: Number(event.target.dataset.itemid),
                                            username: window.username,
                                            act: 'add'});
    if (response.success) {
        showAlert('Success: cart item added');
    } else {
        showAlert(response.message);
    }
}

function addSharedEnterKey() {
    if (event.key === 'Enter') addShared();
}

async function addShared(forever=null) {
    let duration = {
        year: document.getElementById('add-shared-year').value,
        month: document.getElementById('add-shared-month').value,
        day: document.getElementById('add-shared-day').value,
        hour: document.getElementById('add-shared-hour').value,
        minute: document.getElementById('add-shared-minute').value,
        second: document.getElementById('add-shared-second').value
    };
    Object.keys(duration).forEach(x => {
        if (duration[x] === "") duration[x] = 0;
        else duration[x] = Number(duration[x]);
    });
    let data = {
        username: document.getElementById('add-shared-username').value.toLowerCase(),
        act: 'add',
        duration: duration
    };
    if (forever !== null) data.forever = true;
    let response = await postData('/shared', data);
    if (response.success) {
        showAlert('Success: account share added');
        await sleep(2000);
        window.location.reload();
    }
    else showAlert(response.message);
}

async function deleteShared() {
    let response = await postData('/shared', {target: Number(event.target.dataset.userid), act: 'del'});
    if (response.success) {
        showAlert('Success: account share removed');
        await sleep(2000);
        window.location.reload();
    }
    else showAlert(response.message);
}
