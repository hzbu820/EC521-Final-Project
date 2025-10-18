import browser from 'webextension-polyfill';

const form = document.getElementById('settings-form');
const backendInput = document.getElementById('backend-url');
const autoAnnotateInput = document.getElementById('auto-annotate');
const statusNode = document.getElementById('status');

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  form.addEventListener('submit', handleSubmit);
});

async function loadSettings() {
  try {
    const settings = await browser.runtime.sendMessage({ type: 'get-settings' });
    if (!settings) {
      return;
    }

    backendInput.value = settings.backendBaseUrl ?? '';
    autoAnnotateInput.checked = Boolean(settings.autoAnnotate);
  } catch (error) {
    console.warn('Slopspotter popup: failed to load settings', error);
    updateStatus('Could not load settings. Is the background service running?', true);
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  updateStatus('');

  const payload = {
    backendBaseUrl: backendInput.value.trim(),
    autoAnnotate: autoAnnotateInput.checked
  };

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
  backendInput.disabled = !enabled;
  autoAnnotateInput.disabled = !enabled;
  form.querySelector('button[type="submit"]').disabled = !enabled;
}

function updateStatus(message, isError = false) {
  statusNode.textContent = message;
  statusNode.style.color = isError ? '#dc2626' : '#16a34a';
}
