import browser from 'webextension-polyfill';
import { extractPackages } from '../utils/parser';
import {
  ensureStylesInjected,
  renderIndicators,
  renderPending,
  getIndicatorContainer
} from '../utils/dom';

const SNIPPET_ATTR = 'data-slopspotter-snippet-id';
let snippetCounter = 0;
let settings = {
  autoAnnotate: true
};

const nextSnippetId = () => {
  snippetCounter += 1;
  return `snippet-${Date.now()}-${snippetCounter}`;
};

const processedSnippets = new Set();

initialize();

async function initialize() {
  ensureStylesInjected();
  await loadSettings();
  scanForCodeBlocks();

  const observer = new MutationObserver((mutations) => {
    const shouldScan = mutations.some((mutation) =>
      Array.from(mutation.addedNodes).some((node) => containsCode(node))
    );
    if (shouldScan) {
      scanForCodeBlocks();
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  browser.storage.onChanged.addListener((changes, area) => {
    if (area !== 'sync') {
      return;
    }

    if (changes.autoAnnotate) {
      settings.autoAnnotate = changes.autoAnnotate.newValue;
      processedSnippets.clear();
      scanForCodeBlocks();
    }
  });
}

async function loadSettings() {
  try {
    const result = await browser.runtime.sendMessage({ type: 'get-settings' });
    if (result) {
      settings = { ...settings, ...result };
    }
  } catch (error) {
    console.warn('Slopspotter: failed to load settings', error);
  }
}

function containsCode(node) {
  if (!(node instanceof Element)) {
    return false;
  }

  return node.matches('pre') || !!node.querySelector('pre, code');
}

async function scanForCodeBlocks() {
  const codeBlocks = collectCodeBlocks();

  for (const block of codeBlocks) {
    if (processedSnippets.has(block)) {
      continue;
    }

    await analyzeSnippet(block);
  }
}

function collectCodeBlocks() {
  const set = new Set();

  document.querySelectorAll('pre').forEach((pre) => {
    const text = pre.textContent;
    if (text && text.trim().length > 0) {
      set.add(pre);
    }
  });

  document.querySelectorAll('code').forEach((code) => {
    const pre = code.closest('pre');
    if (pre) {
      set.add(pre);
    }
  });

  return Array.from(set);
}

async function analyzeSnippet(snippetElement) {
  const snippetId = snippetElement.getAttribute(SNIPPET_ATTR) ?? nextSnippetId();
  snippetElement.setAttribute(SNIPPET_ATTR, snippetId);

  const codeText = snippetElement.textContent ?? '';
  const packages = extractPackages(codeText);

  if (!packages.length) {
    processedSnippets.add(snippetElement);
    return;
  }

  if (!settings.autoAnnotate) {
    renderManualTrigger(snippetElement, snippetId, packages);
    processedSnippets.add(snippetElement);
    return;
  }

  await runCheck(snippetElement, snippetId, packages);
  processedSnippets.add(snippetElement);
}

function renderManualTrigger(snippetElement, snippetId, packages) {
  const container = getIndicatorContainer(snippetElement);
  container.replaceChildren();

  const button = document.createElement('button');
  button.className = 'slopspotter-action-button';
  button.type = 'button';
  button.textContent = 'Analyze packages';

  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Analyzing...';
    await runCheck(snippetElement, snippetId, packages);
  });

  container.appendChild(button);
}

async function runCheck(snippetElement, snippetId, packages) {
  renderPending(snippetElement);

  try {
    const response = await browser.runtime.sendMessage({
      type: 'check-packages',
      payload: {
        snippetId,
        packages
      }
    });

    if (response) {
      renderIndicators(snippetElement, response);
    }
  } catch (error) {
    console.warn('Slopspotter: background communication failed', error);
    renderIndicators(snippetElement, {
      snippetId,
      packages: packages.map((pkg) => ({
        ...pkg,
        result: {
          riskLevel: 'unknown',
          score: null,
          summary: 'Unable to retrieve metadata for this package. Check manually.'
        }
      })),
      warning: 'Extension could not reach the background service.'
    });
  }
}
