import browser from 'webextension-polyfill';
import { extractPackages } from '../utils/parser';
import {
  ensureStylesInjected,
  renderIndicators,
  renderPending,
  getIndicatorContainer,
  renderError
} from '../utils/dom';

/*
Table of Contents
- State & constants
- Lifecycle: initialize + mutation observer
- Settings loading
- Code discovery & analysis
- Rendering helpers (manual trigger, pending/error)
- Language detection helpers
- Code sanitization
*/

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

initialize(); // kick off setup on load

async function initialize() {
  // Inject styles, hydrate settings, scan current DOM, and watch for changes.
  // This runs once when the content script is loaded into the page.
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
  // Pull synced settings from background; fall back to defaults if missing.
  // This allows user-configured host name and auto-annotate toggle to persist.
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
  // Determine whether a node contains a code block we care about.
  // Accepts <pre> itself or any element containing <pre>/<code>.
  if (!(node instanceof Element)) {
    return false;
  }

  return node.matches('pre') || !!node.querySelector('pre, code');
}

async function scanForCodeBlocks() {
  // Scan the page for code blocks and analyze any new ones.
  // Keeps a Set to avoid reprocessing the same snippet.
  const codeBlocks = collectCodeBlocks();

  for (const block of codeBlocks) {
    if (processedSnippets.has(block)) {
      continue;
    }

    await analyzeSnippet(block);
  }
}

function collectCodeBlocks() {
  // Gather unique <pre> containers with non-empty code content.
  // Also includes <code> elements nested in <pre>.
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
  // Parse code, detect language, extract packages, and dispatch a check.
  // Assigns a stable snippet id for associating responses with DOM nodes.
  const snippetId = snippetElement.getAttribute(SNIPPET_ATTR) ?? nextSnippetId();
  snippetElement.setAttribute(SNIPPET_ATTR, snippetId);

  const rawText = snippetElement.textContent ?? '';
  const codeText = sanitizeCodeText(rawText);
  const detectedLanguage = detectLanguage(snippetElement);
  if (detectedLanguage) {
    snippetElement.setAttribute('data-slopspotter-language', detectedLanguage);
  }
  const packages = extractPackages(codeText, { language: detectedLanguage });

  if (!packages.length) {
    console.debug('Slopspotter: no packages detected', {
      snippetId,
      language: detectedLanguage,
      codePreview: codeText.slice(0, 120)
    });
    processedSnippets.add(snippetElement);
    return;
  }

  console.debug('Slopspotter: packages detected', {
    snippetId,
    language: detectedLanguage,
    packages: packages.map((p) => p.name),
    count: packages.length,
    codePreview: codeText.slice(0, 120)
  });

  if (!settings.autoAnnotate) {
    renderManualTrigger(snippetElement, snippetId, packages);
    processedSnippets.add(snippetElement);
    return;
  }

  await runCheck(snippetElement, snippetId, packages);
  processedSnippets.add(snippetElement);
}

function renderManualTrigger(snippetElement, snippetId, packages) {
  // Render a manual "Analyze" button when autoAnnotate is disabled.
  // Clicking triggers the same runCheck path used for auto mode.
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
  // Ask the background to check packages; show pending/error UI.
  // On failure, show retry so users can re-run after transient issues.
  console.debug('Slopspotter: running check', { snippetId, packages });
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
    renderError(snippetElement, 'Extension could not reach the background service.', () =>
      runCheck(snippetElement, snippetId, packages)
    );
  }
}

function detectLanguage(snippetElement) {
  // Guess language from data attributes or class names near the snippet.
  // Walks the snippet and a few ancestors to find hints.
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
  // Inspect dataset/attrs/classList for language hints.
  // Returns a normalized language string or undefined.
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
  // Normalize common language class tokens (e.g., language-py → python).
  // Supports multiple class naming conventions.
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

const KNOWN_LANGUAGE_LABELS = new Set([
  ...Object.keys(DIRECT_LANGUAGE_TOKENS),
  'python',
  'javascript',
  'typescript',
  'bash',
  'shell',
  'go',
  'rust',
  'json',
  'yaml',
  'java',
  'c',
  'cpp',
  'c++',
  'c#'
]);

function sanitizeCodeText(text) {
  // Strip UI artifacts (language labels, "Copy code") before parsing.
  // Ensures extractPackages sees only code, not chrome from the host site.
  if (!text) return '';
  // Remove common UI artifacts like "Copy code"
  let cleaned = text.replace(/\bcopy code\b/gi, '');

  const lines = cleaned.split('\n').map((line) => line.trimEnd());

  const labelPattern = new RegExp(
    `^\\s*(?:${Array.from(KNOWN_LANGUAGE_LABELS)
      .map((l) => l.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'))
      .join('|')})(?:\\s*copy\\s*code)?\\s*`,
    'i'
  );

  // Drop or strip leading language labels, even if attached to code
  while (lines.length) {
    const first = lines[0].trim();
    if (!first) {
      lines.shift();
      continue;
    }
    if (labelPattern.test(first) && first.replace(labelPattern, '') === '') {
      lines.shift();
      continue;
    }
    break;
  }

  // Strip label prefixes that are glued to code (e.g., "pythonCopy codeimport numpy")
  const stripped = lines.map((line) => line.replace(labelPattern, ''));

  cleaned = stripped.join('\n');
  return cleaned;
}
