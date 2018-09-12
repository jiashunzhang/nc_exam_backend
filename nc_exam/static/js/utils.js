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
function objectDeepCopy(src) {
    let ret = undefined;
    if(Array.isArray(src))
        ret = [];
    else if(src instanceof Object)
        ret = {};
    else
        return src;

    for(let p in src) {
        let copy = src[p];
        if(Array.isArray(copy) || copy instanceof Object)
            ret[p] = arguments.callee(copy);
        else
            ret[p] = src[p];
    }
    return ret;
}
function datetimeFormat(d, fmt) {
    var o = {
        "M+": d.getMonth() + 1,
        "d+": d.getDate(),
        "h+": d.getHours(),
        "m+": d.getMinutes(),
        "s+": d.getSeconds(),
        "q+": Math.floor((d.getMonth() + 3) / 3),
        "S": d.getMilliseconds()
    };
    if(/(y+)/.test(fmt))
        fmt = fmt.replace(RegExp.$1, (d.getFullYear() + "").substr(4 - RegExp.$1.length));
    for(let k in o)
        if(new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
    return fmt;
}
