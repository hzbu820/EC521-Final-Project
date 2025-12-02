import browser from "webextension-polyfill";

/*
Table of Contents
- DOM refs & state
- Lifecycle: load + event binding
- Settings load/save
- Status handling (form toggle, status text, host ping/pill)
*/

const form = document.getElementById("settings-form");
const nativeHostInput = document.getElementById("native-host");
const autoAnnotateInput = document.getElementById("auto-annotate");
const statusNode = document.getElementById("status");
const hostStatusNode = document.getElementById("host-status");

document.addEventListener("DOMContentLoaded", () => {
  // Hydrate settings and bind form events (submit + host ping on blur).
  loadSettings();
  form.addEventListener("submit", handleSubmit);
  nativeHostInput.addEventListener("blur", () => pingHost(nativeHostInput.value.trim()));
});

async function loadSettings() {
  // Fetch current settings from background and prime the form controls.
  try {
    const settings = await browser.runtime.sendMessage({
      type: "get-settings",
    });
    if (!settings) {
      return;
    }

    autoAnnotateInput.checked = Boolean(settings.autoAnnotate);
    nativeHostInput.value = settings.nativeHostName ?? "";
    if (settings.nativeHostName) {
      pingHost(settings.nativeHostName);
    }
  } catch (error) {
    console.warn("Slopspotter popup: failed to load settings", error);
    updateStatus(
      "Could not load settings. Is the background service running?",
      true,
    );
  }
}

async function handleSubmit(event) {
  // Save settings to background and re-ping host.
  event.preventDefault();
  updateStatus("");

  const host = nativeHostInput.value.trim();
  if (!host) {
    updateStatus("Enter the native host ID.", true);
    return;
  }

  const payload = {
    autoAnnotate: autoAnnotateInput.checked,
    nativeHostName: host,
  };

  try {
    toggleForm(false);
    await browser.runtime.sendMessage({ type: "save-settings", payload });
    updateStatus("Settings saved successfully.");
    pingHost(host);
  } catch (error) {
    console.error("Slopspotter popup: failed to save settings", error);
    updateStatus("Failed to save settings. Try again.", true);
  } finally {
    toggleForm(true);
  }
}

function toggleForm(enabled) {
  // Enable/disable form during async save.
  autoAnnotateInput.disabled = !enabled;
  nativeHostInput.disabled = !enabled;
  form.querySelector('button[type="submit"]').disabled = !enabled;
}

function updateStatus(message, isError = false) {
  // Update inline status text with success/error styling.
  statusNode.textContent = message;
  statusNode.className = "status";
  if (!message) {
    return;
  }
  statusNode.className = `status ${isError ? "status--error" : "status--success"}`;
}

async function pingHost(host) {
  // Try a ping to the native host to drive the status pill.
  // Uses a simple "ping" message; absence of response marks unreachable.
  if (!host) {
    setHostStatus("idle", "Enter host ID");
    return;
  }
  setHostStatus("idle", "Checking...");
  try {
    const response = await browser.runtime.sendNativeMessage(host, "ping");
    if (response) {
      setHostStatus("connected", "Connected");
      return;
    }
    setHostStatus("error", "Unreachable");
  } catch (error) {
    setHostStatus("error", "Unreachable");
  }
}

function setHostStatus(state, text) {
  // Update the status pill appearance/text based on host reachability.
  if (!hostStatusNode) return;
  hostStatusNode.textContent = text;
  hostStatusNode.className = "status-pill";
  if (state === "connected") {
    hostStatusNode.classList.add("status-pill--connected");
  } else if (state === "error") {
    hostStatusNode.classList.add("status-pill--error");
  } else {
    hostStatusNode.classList.add("status-pill--idle");
  }
}
