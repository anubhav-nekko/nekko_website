var swiper = new Swiper(".mySwiper", {
    spaceBetween: 30,
    effect: "fade",
    loop: true,
    navigation: {
        nextEl: ".next-btn",
        prevEl: ".prev-btn",
    },
    pagination: {
        el: ".swiper-pagination",
        clickable: true,
    },
});

