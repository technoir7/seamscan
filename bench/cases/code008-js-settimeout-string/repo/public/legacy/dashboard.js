function schedulePanelRefresh(panelId, seconds) {
  setTimeout("refreshPanel('" + panelId + "')", seconds * 1000);
}

function refreshPanel(panelId) {
  fetch("/api/panels/" + panelId)
    .then((r) => r.json())
    .then((data) => {
      document.getElementById(panelId).textContent = data.value;
      schedulePanelRefresh(panelId, data.refreshSeconds);
    });
}

window.refreshPanel = refreshPanel;
