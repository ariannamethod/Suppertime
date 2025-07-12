function goBack() {
    window.parent.postMessage('close', '*');
}

function randomGlitch() {
    const paras = document.querySelectorAll('p');
    if (paras.length === 0) return;
    const el = paras[Math.floor(Math.random() * paras.length)];
    el.classList.add('glitch');
    setTimeout(() => el.classList.remove('glitch'), 1500);
}
setInterval(randomGlitch, 5000);

