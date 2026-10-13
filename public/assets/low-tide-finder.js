/* Small, dependency-free enhancement. All NOAA events remain visible without JS. */
(() => {
  "use strict";
  for (const panel of document.querySelectorAll(".c2-low-finder")) {
    const picker = panel.querySelector(".c2-low-finder-daypart");
    const rows = [...panel.querySelectorAll(".c2-low-finder-row")];
    const status = panel.querySelector(".c2-low-finder-status");
    if (!picker || !status || rows.length === 0) continue;

    const update = () => {
      const period = picker.value;
      let shown = 0;
      for (const row of rows) {
        const visible = period === "all" || row.dataset.timeBand === period;
        row.hidden = !visible;
        if (visible) shown += 1;
      }
      status.textContent = shown === 0
        ? "No predicted low-tide events in this time period. Choose another time."
        : `Showing ${shown} predicted low-tide event${shown === 1 ? "" : "s"}.`;
    };
    picker.addEventListener("change", update);
    update();
  }
})();
