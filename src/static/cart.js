
async function addToCart() {
    let response = await postData('/buy', {productID: event.target.dataset.itemid,
                                           username: window.username});
    if (response.success) {
        showAlert('success!');
    } else {
        showAlert(response.message);
    }
}
