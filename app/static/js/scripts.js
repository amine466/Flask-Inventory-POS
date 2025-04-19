const sidebarToggle = document.querySelector("#sidebar-toggle");
const sidebar = document.querySelector("#sidebar");

sidebarToggle.addEventListener("click", function(){
    sidebar.classList.toggle("collapsed");
});

function handleResize() {
    if (window.innerWidth <= 900) {
        sidebar.classList.add("collapsed");
    } else {
        sidebar.classList.remove("collapsed");
    }
}

handleResize();
window.addEventListener("resize", handleResize);