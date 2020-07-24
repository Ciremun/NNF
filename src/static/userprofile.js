
async function logout() {
    let response = await postData('/logout', {SID: window.getCookie('SID')});
    if (response.success) {
        document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = `${location.protocol}//${window.location.host}`;
    } else {
        window.location.reload(true);
    }
}


async function addToCart(type) {
    if (type === 'complex') {
        let item = event.path.find(e => e.classList.contains('category_head'))
                                .getElementsByClassName('category_label')[0].innerText.split(' '),
            displayname = document.getElementById('displayname').innerText,
            response = await postData('/buy', {SID: window.getCookie('SID'), item: item.slice(0, -2).join(' '),
                                            price: `${item[item.length - 2]}`,
                                            type: type, username: displayname.toLowerCase()});
            if (response.success) {
                alert('success');
            } else {
                alert(response.message);
            }
    } else if (type === 'menu') {
        alert('wip');
    }
}
