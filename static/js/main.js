(() => {
    const root = document.documentElement;
    const nav = document.querySelector(".glass-nav");
    const themeToggle = document.getElementById("themeToggle");
    const themeToggleMobile = document.getElementById("themeToggleMobile");
    const backToTop = document.getElementById("backToTop");
    const year = document.getElementById("currentYear");

    if (year) year.textContent = new Date().getFullYear();

    const savedTheme = localStorage.getItem("sms-theme");
    if (savedTheme === "dark") {
        root.setAttribute("data-bs-theme", "dark");
    }

    function syncThemeIcon() {
        const dark = root.getAttribute("data-bs-theme") === "dark";
        if (themeToggle) {
            themeToggle.innerHTML = dark
                ? '<i class="bi bi-sun"></i>'
                : '<i class="bi bi-moon-stars"></i>';
            themeToggle.setAttribute(
                "aria-label",
                dark ? "Activar tema claro" : "Activar tema oscuro"
            );
        }
        if (themeToggleMobile) {
            themeToggleMobile.innerHTML = dark
                ? '<i class="bi bi-sun"></i><span>Activar tema claro</span>'
                : '<i class="bi bi-moon-stars"></i><span>Activar tema oscuro</span>';
        }
    }

    syncThemeIcon();

    function toggleTheme() {
        const dark = root.getAttribute("data-bs-theme") === "dark";
        root.setAttribute("data-bs-theme", dark ? "light" : "dark");
        localStorage.setItem("sms-theme", dark ? "light" : "dark");
        syncThemeIcon();
    }

    themeToggle?.addEventListener("click", toggleTheme);
    themeToggleMobile?.addEventListener("click", toggleTheme);

    function onScroll() {
        nav?.classList.toggle("scrolled", window.scrollY > 20);
        backToTop?.classList.toggle("show", window.scrollY > 500);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    backToTop?.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    document.querySelectorAll(".navbar-collapse .nav-link").forEach(link => {
        link.addEventListener("click", () => {
            const menu = document.getElementById("menuPrincipal");
            if (menu?.classList.contains("show") && window.bootstrap) {
                bootstrap.Collapse.getOrCreateInstance(menu).hide();
            }
        });
    });
})();


// Entrega 2: cerrar el menú móvil al navegar a un enlace.
document.querySelectorAll('#menuMovil a').forEach((link) => {
    link.addEventListener('click', () => {
        const element = document.getElementById('menuMovil');
        if (element && window.bootstrap) {
            const instance = bootstrap.Offcanvas.getInstance(element);
            if (instance) instance.hide();
        }
    });
});

// Llevar el foco al buscador cuando se abre el modal.
const modalBuscar = document.getElementById('modalBuscar');
if (modalBuscar) {
    modalBuscar.addEventListener('shown.bs.modal', () => {
        const input = modalBuscar.querySelector('input[name="q"]');
        if (input) input.focus();
    });
}


// ============================================================
// ENTREGA 7 · Animaciones suaves y accesibles
// ============================================================
(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const progress = document.getElementById("scrollProgress");

    function updateProgress() {
        if (!progress) return;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
        progress.style.width = `${Math.min(100, Math.max(0, pct))}%`;
    }

    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
    updateProgress();

    const revealItems = [...document.querySelectorAll("[data-reveal]")];

    if (reduceMotion || !("IntersectionObserver" in window)) {
        revealItems.forEach(el => el.classList.add("is-visible"));
    } else {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });

        revealItems.forEach((el, index) => {
            el.style.transitionDelay = `${Math.min(index % 4, 3) * 70}ms`;
            revealObserver.observe(el);
        });
    }

    const counterItems = [...document.querySelectorAll("[data-counter]")];

    function animateCounter(el) {
        const end = Number(el.dataset.counter || 0);
        if (!Number.isFinite(end)) return;

        if (reduceMotion) {
            el.textContent = end;
            return;
        }

        const duration = 900;
        const startTime = performance.now();

        function tick(now) {
            const p = Math.min(1, (now - startTime) / duration);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(end * eased);
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    if ("IntersectionObserver" in window && !reduceMotion) {
        const counterObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.55 });

        counterItems.forEach(el => counterObserver.observe(el));
    } else {
        counterItems.forEach(animateCounter);
    }

    if (!reduceMotion && window.matchMedia("(pointer: fine)").matches) {
        document.querySelectorAll(".tilt-lite").forEach(card => {
            card.addEventListener("pointermove", event => {
                const rect = card.getBoundingClientRect();
                const x = (event.clientX - rect.left) / rect.width - 0.5;
                const y = (event.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `perspective(900px) rotateX(${y * -3}deg) rotateY(${x * 3}deg) translateY(-2px)`;
            });

            card.addEventListener("pointerleave", () => {
                card.style.transform = "";
            });
        });
    }

    const mensaje = document.getElementById("mensaje");
    const messageCount = document.getElementById("messageCount");
    if (mensaje && messageCount) {
        const sync = () => messageCount.textContent = mensaje.value.length;
        mensaje.addEventListener("input", sync);
        sync();
    }

    window.setTimeout(() => {
        document.querySelectorAll(".flash7.alert").forEach(alert => {
            if (window.bootstrap) {
                bootstrap.Alert.getOrCreateInstance(alert).close();
            }
        });
    }, 4200);
})();

// ============================================================
// ENTREGA 9 · videos públicos y hero dinámico
// ============================================================
(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const mediaVideos = [...document.querySelectorAll('.home9-video-media video, .videos9-media video')];

    if (!reduceMotion && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target;
                if (entry.isIntersecting) {
                    video.play().catch(() => {});
                } else {
                    video.pause();
                }
            });
        }, { threshold: 0.55 });
        mediaVideos.forEach(v => observer.observe(v));
    } else {
        mediaVideos.forEach(v => v.pause());
    }

    const carousel = document.getElementById('hero9Carousel');
    if (carousel) {
        carousel.addEventListener('slide.bs.carousel', () => {
            carousel.querySelectorAll('video').forEach(video => {
                if (!video.closest('.carousel-item')?.classList.contains('active')) video.pause();
            });
        });
        carousel.addEventListener('slid.bs.carousel', () => {
            if (reduceMotion) return;
            const video = carousel.querySelector('.carousel-item.active video');
            if (video) video.play().catch(() => {});
        });
    }
})();


// Ajuste Entrega 9: cerrar el panel Explorar al navegar.
document.querySelectorAll('#explorePanel a').forEach((link) => {
    link.addEventListener('click', () => {
        const element = document.getElementById('explorePanel');
        if (element && window.bootstrap) {
            const instance = bootstrap.Offcanvas.getInstance(element);
            if (instance) instance.hide();
        }
    });
});
