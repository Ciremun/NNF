
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
