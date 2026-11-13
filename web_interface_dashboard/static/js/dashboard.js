// Make sure every Plotly chart fits its card once the page layout is ready
window.addEventListener("load", () => {
    document.querySelectorAll(".js-plotly-plot").forEach((chart) => {
        Plotly.Plots.resize(chart);
    });
});