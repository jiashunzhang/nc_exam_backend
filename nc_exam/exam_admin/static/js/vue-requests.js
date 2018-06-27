function v_requests(that,
                    url = "",
                    success = (result) => { console.log(result); },
                    error = (err) => { console.log(err); },
                    data = {},
                    headers = { "Content-Type": "application/x-www-form-urlencoded" }) {
    that.$http.post(
        url,
        data,
        {
            headers: headers,
            emulateJSON: true
        }
    ).then(success)
    .catch(error);
}
