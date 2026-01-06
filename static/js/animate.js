document.addEventListener("DOMContentLoaded", () => {
    const counters = document.querySelectorAll(".count");

    counters.forEach(counter => {
        const target = +counter.dataset.target;
        let current = 0;
        const step = target / 60;

        const update = () => {
            current += step;
            if (current < target) {
                counter.innerText = Math.floor(current);
                requestAnimationFrame(update);
            } else {
                counter.innerText = target;
            }
        };
        update();
    });
});
