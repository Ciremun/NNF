
async function addToCart(type) {
    if (type === 'complex') {
        let item = event.path.find(e => e.classList.contains('category_head'))
                             .getElementsByClassName('category_label')[0].innerText.split(' '),
            response = await postData('/buy', {item: item.slice(0, -2).join(' '), price: `${item[item.length - 2]}`,
                                               type: type, username: window.username});
            if (response.success) {
                alert('success');
            } else {
                alert(response.message);
            }
    } else if (type === 'menu') {
        alert('wip');
    }
}
