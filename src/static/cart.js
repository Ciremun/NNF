
async function addToCart() {
    let response = await postData('/cart', {productID: Number(event.target.dataset.itemid),
                                           username: window.username,
                                           act: 'add'});
    if (response.success) {
        showAlert('success!');
    } else {
        showAlert(response.message);
    }
}
