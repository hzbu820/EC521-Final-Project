import browser from 'webextension-polyfill';

const form = document.getElementById('settings-form');
const backendModeSelect = document.getElementById('backend-mode');
const backendInput = document.getElementById('backend-url');
const nativeHostInput = document.getElementById('native-host');
const autoAnnotateInput = document.getElementById('auto-annotate');
const statusNode = document.getElementById('status');
const httpSettingsGroup = document.getElementById('http-settings');
const nativeSettingsGroup = document.getElementById('native-settings');

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  form.addEventListener('submit', handleSubmit);
  backendModeSelect.addEventListener('change', updateConnectionVisibility);
});

async function loadSettings() {
  try {
    const settings = await browser.runtime.sendMessage({ type: 'get-settings' });
    if (!settings) {
      return;
    }

    backendModeSelect.value = settings.backendMode ?? 'http';
    backendInput.value = settings.backendBaseUrl ?? '';
    nativeHostInput.value = settings.nativeHostName ?? '';
    autoAnnotateInput.checked = Boolean(settings.autoAnnotate);
    updateConnectionVisibility();
  } catch (error) {
    console.warn('Slopspotter popup: failed to load settings', error);
    updateStatus('Could not load settings. Is the background service running?', true);
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  updateStatus('');

  const backendMode = backendModeSelect.value;
  const httpUrl = backendInput.value.trim();
  const nativeHost = nativeHostInput.value.trim();

  const payload = {
    backendMode,
    backendBaseUrl: httpUrl,
    nativeHostName: nativeHost,
    autoAnnotate: autoAnnotateInput.checked
  };

  if (backendMode === 'http' && !httpUrl) {
    updateStatus('Enter the HTTP backend base URL.', true);
    return;
  }

  if (backendMode === 'native' && !nativeHost) {
    updateStatus('Enter the native messaging host ID.', true);
    return;
  }

  try {
    toggleForm(false);
    await browser.runtime.sendMessage({ type: 'save-settings', payload });
    updateStatus('Settings saved successfully.');
  } catch (error) {
    console.error('Slopspotter popup: failed to save settings', error);
    updateStatus('Failed to save settings. Try again.', true);
  } finally {
    toggleForm(true);
  }
}

function toggleForm(enabled) {
  backendModeSelect.disabled = !enabled;
  backendInput.disabled = !enabled;
  nativeHostInput.disabled = !enabled;
  autoAnnotateInput.disabled = !enabled;
  form.querySelector('button[type="submit"]').disabled = !enabled;
}

function updateStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.style.color = isError ? '#dc2626' : '#16a34a';
}

function updateConnectionVisibility() {
  const mode = backendModeSelect.value;
  if (mode === 'native') {
    httpSettingsGroup.setAttribute('hidden', '');
    nativeSettingsGroup.removeAttribute('hidden');
  } else {
    nativeSettingsGroup.setAttribute('hidden', '');
    httpSettingsGroup.removeAttribute('hidden');
  }
}
