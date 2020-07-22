
async function logout() {
    response = await postData('/logout', {SID: window.getCookie('SID')});
    if (response.success) {
        document.cookie = "SID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = `${location.protocol}//${window.location.host}`;
    } else {
        window.location.reload(true);
    }
}
