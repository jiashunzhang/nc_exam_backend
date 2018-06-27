function getInnerText(element) {
    return (typeof element.textContent == "string" ? element.textContent : element.innerText);
}

function setInnerText(element, text) {
    if(typeof element.textContent == "string") {
        element.textContent = text;
    } else {
        element.innerText = text;
    }
}
