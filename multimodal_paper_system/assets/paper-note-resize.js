(function () {
  if (window.innerWidth <= 1320) return;

  const key = "multimodal_paper_note_width";
  const root = document.documentElement;
  const handle = document.querySelector(".note-resizer");
  if (!handle) return;

  try {
    const raw = localStorage.getItem(key);
    const width = Number(raw);
    if (!Number.isNaN(width) && width >= 820 && width <= 1400) {
      root.style.setProperty("--note-content-width", `${width}px`);
    }
  } catch {}

  let resizing = false;

  handle.onpointerdown = event => {
    resizing = true;
    handle.classList.add("dragging");
    handle.setPointerCapture(event.pointerId);
  };

  handle.onpointermove = event => {
    if (!resizing) return;
    const noteWidth = Math.max(820, Math.min(1400, window.innerWidth - event.clientX - 120));
    root.style.setProperty("--note-content-width", `${noteWidth}px`);
  };

  const stop = event => {
    if (!resizing) return;
    resizing = false;
    handle.classList.remove("dragging");
    try {
      handle.releasePointerCapture(event.pointerId);
    } catch {}
    const value = getComputedStyle(root).getPropertyValue("--note-content-width").trim().replace("px", "");
    localStorage.setItem(key, value);
  };

  handle.onpointerup = stop;
  handle.onpointercancel = stop;
})();
