function logout() {
    document.cookie = "sessionID=";
    window.location.href = "/";
}