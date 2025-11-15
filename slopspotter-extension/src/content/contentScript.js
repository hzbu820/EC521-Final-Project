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
  const detectedLanguage = detectLanguage(snippetElement);
  if (detectedLanguage) {
    snippetElement.setAttribute('data-slopspotter-language', detectedLanguage);
  }
  const packages = extractPackages(codeText, { language: detectedLanguage });

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

function detectLanguage(snippetElement) {
  if (!snippetElement) {
    return undefined;
  }

  const candidates = [];
  const codeElement = snippetElement.matches('code')
    ? snippetElement
    : snippetElement.querySelector('code');
  if (codeElement) {
    candidates.push(codeElement);
  }
  candidates.push(snippetElement);

  let ancestor = snippetElement.parentElement;
  while (ancestor && candidates.length < 6) {
    candidates.push(ancestor);
    ancestor = ancestor.parentElement;
  }

  for (const element of candidates) {
    const language = extractLanguageFromElement(element);
    if (language) {
      return language;
    }
  }

  return undefined;
}

function extractLanguageFromElement(element) {
  if (!element) {
    return undefined;
  }

  const datasetLanguage = element.dataset?.language || element.dataset?.lang;
  if (datasetLanguage && datasetLanguage.trim()) {
    return datasetLanguage.trim().toLowerCase();
  }

  const attrLanguage =
    element.getAttribute('data-language') ||
    element.getAttribute('data-lang') ||
    element.getAttribute('lang');
  if (attrLanguage && attrLanguage.trim()) {
    return attrLanguage.trim().toLowerCase();
  }

  const classList = element.classList ? Array.from(element.classList) : [];
  for (const token of classList) {
    const normalized = normalizeLanguageToken(token);
    if (normalized) {
      return normalized;
    }
  }

  return undefined;
}

const LANGUAGE_CLASS_PATTERNS = [
  /^language-([a-z0-9+#]+)/i,
  /^lang-([a-z0-9+#]+)/i,
  /^language_([a-z0-9+#]+)/i,
  /^lang_([a-z0-9+#]+)/i,
  /^highlight-source-([a-z0-9+#]+)/i,
  /^sourcecode-([a-z0-9+#]+)/i
];

const DIRECT_LANGUAGE_TOKENS = {
  python: 'python',
  py: 'python',
  javascript: 'javascript',
  js: 'javascript',
  typescript: 'typescript',
  ts: 'typescript',
  rust: 'rust',
  go: 'go',
  golang: 'go',
  shell: 'shell',
  bash: 'shell',
  sh: 'shell'
};

function normalizeLanguageToken(token) {
  if (!token) {
    return undefined;
  }
  const lower = token.toLowerCase();
  for (const pattern of LANGUAGE_CLASS_PATTERNS) {
    const match = lower.match(pattern);
    if (match) {
      return match[1];
    }
  }
  const direct = DIRECT_LANGUAGE_TOKENS[lower];
  if (direct) {
    return direct;
  }
  return undefined;
}
