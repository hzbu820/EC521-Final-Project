import browser from "webextension-polyfill";

const form = document.getElementById("settings-form");
const nativeHostInput = document.getElementById("native-host");
const autoAnnotateInput = document.getElementById("auto-annotate");
const statusNode = document.getElementById("status");
const hostStatusNode = document.getElementById("host-status");

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  form.addEventListener("submit", handleSubmit);
  nativeHostInput.addEventListener("blur", () => pingHost(nativeHostInput.value.trim()));
});

async function loadSettings() {
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
  autoAnnotateInput.disabled = !enabled;
  nativeHostInput.disabled = !enabled;
  form.querySelector('button[type="submit"]').disabled = !enabled;
}

function updateStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.className = "status";
  if (!message) {
    return;
  }
  statusNode.className = `status ${isError ? "status--error" : "status--success"}`;
}

async function pingHost(host) {
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
