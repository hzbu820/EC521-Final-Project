import browser from 'webextension-polyfill';

const STYLE_ID = 'slopspotter-style';

const STYLE_CONTENT = `
.slopspotter-indicators {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 12px;
  margin-bottom: 8px;
  overflow: visible !important; /* Prevent clipping */
  position: relative !important;
  z-index: 2147483640 !important; /* Ensure it sits above other content */
}

.slopspotter-chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 9999px;
  color: #0f172a;
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.18), rgba(148, 163, 184, 0.08));
  border: 1.5px solid rgba(148, 163, 184, 0.45);
  cursor: default;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 4px 10px rgba(15, 23, 42, 0.08);
  transition: box-shadow 0.15s ease, background 0.15s ease;
  z-index: 2147483645;
  overflow: visible !important; /* Prevent clipping of tooltip */
}

.slopspotter-chip:hover,
.slopspotter-chip:focus-visible {
  /* transform: translateY(-1px); Removed to prevent breaking fixed positioning */
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 8px 16px rgba(15, 23, 42, 0.12);
}

.slopspotter-chip[data-risk="low"] {
  border-color: rgba(16, 185, 129, 0.65);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.22), rgba(16, 185, 129, 0.1));
}

.slopspotter-chip[data-risk="medium"] {
  border-color: rgba(245, 158, 11, 0.65);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.22), rgba(245, 158, 11, 0.1));
}

.slopspotter-chip[data-risk="high"] {
  border-color: rgba(244, 63, 94, 0.7);
  background: linear-gradient(135deg, rgba(244, 63, 94, 0.24), rgba(244, 63, 94, 0.12));
  color: #7f1d1d;
}

.slopspotter-chip__dot {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
}

.slopspotter-chip__label {
  font-weight: 600;
  color: inherit;
}

.slopspotter-chip__tooltip {
  visibility: hidden;
  position: fixed !important; /* Use fixed to escape parent overflow */
  top: 0;
  left: 0;
  min-width: 230px;
  max-width: 300px;
  padding: 12px 14px 24px 14px !important; /* Force padding */
  box-sizing: border-box !important;
  height: auto !important;
  min-height: fit-content !important;
  max-height: none !important; /* Ensure no height limit */
  overflow: visible !important; /* Prevent clipping */
  display: flex !important; /* Use flex for robust sizing */
  flex-direction: column !important;
  height: auto !important;
  width: auto !important;
  border-radius: 14px;
  background: #0f172a;
  color: #f8fafc;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.25);
  z-index: 2147483647;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s ease;
  pointer-events: none;
}

.slopspotter-chip__tooltip.slopspotter-tooltip--visible {
  visibility: visible;
  pointer-events: auto;
  opacity: 1;
  transform: translateY(0);
}

.slopspotter-chip__tooltip h4 {
  margin: 0 0 6px 0;
  font-size: 13px;
  font-weight: 700;
  color: #e2e8f0;
}

.slopspotter-chip__tooltip p {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
}

.slopspotter-chip__tooltip a {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: #38bdf8;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(56, 189, 248, 0.4);
  background: rgba(56, 189, 248, 0.12);
}

.slopspotter-deep-scan-btn {
  display: flex !important;
  width: auto !important; /* Match content width */
  margin: 8px 0 0 0 !important; /* Match link margin */
  justify-content: flex-start !important; /* Align words to left */
  align-items: center !important;
  box-sizing: border-box !important;
  gap: 6px;
  font-size: 12px !important; /* Match metadata font size */
  line-height: 1.4 !important;
  color: #fca5a5 !important;
  padding: 6px 10px !important; /* Exact match to metadata padding */
  min-height: 0 !important;
  border-radius: 8px !important; /* Match metadata border radius */
  border: 1px solid rgba(240, 89, 89, 0.5) !important;
  background: rgba(206, 68, 68, 0.25) !important;
  box-shadow: none !important;
  cursor: pointer;
  font-weight: 500 !important;
  transition: all 0.2s ease;
  text-shadow: none !important;
  text-align: left !important; /* Ensure text aligns left */
  height: auto !important;
}

.slopspotter-deep-scan-btn:hover {
  background: rgba(220, 38, 38, 0.35) !important;
  border-color: rgba(239, 68, 68, 0.8) !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
}

.slopspotter-deep-scan-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.slopspotter-deep-scan-btn.malicious {
  /* Inherit all base styles (background, border, color, padding, alignment) */
  opacity: 1 !important; /* Override disabled opacity */
  cursor: default !important;
  box-shadow: none !important;
}

.slopspotter-deep-scan-btn .icon {
  font-size: 14px;
}

.slopspotter-deep-scan-result {
  margin-top: 10px;
  padding: 12px; /* More padding for result box */
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.5;
  margin-bottom: 8px;
  height: auto !important;
  min-height: 0 !important;
  flex-shrink: 0 !important; /* Prevent shrinking */
  overflow: visible !important;
}

.slopspotter-deep-scan-result.safe {
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.4);
  color: #86efac;
}

.slopspotter-deep-scan-result.malicious {
  background: rgba(69, 10, 10, 0.95) !important;
  border: 1px solid rgba(248, 113, 113, 0.5) !important;
  color: #fca5a5 !important;
  text-align: left;
}

.slopspotter-deep-scan-result.malicious strong {
  color: #ffffff !important;
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
}

.slopspotter-deep-scan-result.error {
  background: rgba(148, 163, 184, 0.15);
  border: 1px solid rgba(148, 163, 184, 0.4);
  color: #cbd5e1;
}

.slopspotter-warning {
  font-size: 11px;
  background: rgba(234, 179, 8, 0.12);
  border: 1px solid rgba(234, 179, 8, 0.35);
  padding: 8px 12px;
  border-radius: 9px;
  color: #854d0e;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 6px 14px rgba(234, 179, 8, 0.15);
}
.slopspotter-warning .slopspotter-spinner {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  border: 2px solid rgba(148, 163, 184, 0.5);
  border-top-color: rgba(15, 23, 42, 0.85);
  animation: slopspotter-spin 0.8s linear infinite;
}

.slopspotter-action-button {
  appearance: none;
  border: 1px solid rgba(59, 130, 246, 0.6);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(59, 130, 246, 0.1));
  color: #1d4ed8;
  font-size: 12px;
  padding: 7px 14px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s ease-in-out, color 0.2s ease-in-out, transform 0.1s ease-in-out;
}

.slopspotter-action-button:hover {
  background: rgba(59, 130, 246, 0.25);
  transform: translateY(-1px);
}

.slopspotter-action-button:disabled {
  opacity: 0.6;
  cursor: progress;
}

.slopspotter-chip__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.slopspotter-chip__tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(148, 163, 184, 0.18);
  color: #e2e8f0;
}

@keyframes slopspotter-spin {
  to {
    transform: rotate(360deg);
  }
}
`;

const RISK_COLORS = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#ef4444',
  unknown: '#94a3b8'
};

let activeChip = null;
let documentClickBound = false;

export const ensureStylesInjected = () => {
  let style = document.getElementById(STYLE_ID);
  if (!style) {
    style = document.createElement('style');
    style.id = STYLE_ID;
    document.head?.appendChild(style);
  }
  // Always update the content to ensure new styles are applied
  style.textContent = STYLE_CONTENT;
};

export const getIndicatorContainer = (snippetElement) => {
  const parent = snippetElement.parentElement ?? snippetElement;
  const snippetId = snippetElement.getAttribute('data-slopspotter-snippet-id') || '';
  const selector = `:scope > .slopspotter-indicators[data-for="${snippetId}"]`;
  const existing = parent.querySelector(selector);
  if (existing) {
    return existing;
  }

  const container = document.createElement('div');
  container.className = 'slopspotter-indicators';
  container.dataset.for = snippetId;
  parent.insertBefore(container, snippetElement);
  return container;
};

export const renderPending = (snippetElement, message = 'Slopspotter is checking packages...') => {
  const container = getIndicatorContainer(snippetElement);
  container.replaceChildren();

  const pending = document.createElement('div');
  pending.className = 'slopspotter-warning';

  const spinner = document.createElement('span');
  spinner.className = 'slopspotter-spinner';

  const text = document.createElement('span');
  text.textContent = message;

  pending.append(spinner, text);
  container.appendChild(pending);
};

export const renderError = (snippetElement, message, onRetry) => {
  const container = getIndicatorContainer(snippetElement);
  container.replaceChildren();

  const warning = document.createElement('div');
  warning.className = 'slopspotter-warning';
  warning.textContent = message;

  if (typeof onRetry === 'function') {
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'slopspotter-action-button';
    retry.textContent = 'Retry';
    retry.addEventListener('click', onRetry);
    warning.appendChild(retry);
  }

  container.appendChild(warning);
};

export const renderIndicators = (snippetElement, response) => {
  if (!snippetElement || !response) {
    return;
  }

  const container = getIndicatorContainer(snippetElement);
  container.replaceChildren();

  if (response.warning) {
    container.appendChild(createWarningNode(response.warning));
  }

  for (const pkg of response.packages) {
    container.appendChild(createChip(pkg));
  }
};

const createWarningNode = (warning) => {
  const node = document.createElement('div');
  node.className = 'slopspotter-warning';
  node.textContent = warning;
  return node;
};

const createChip = (pkg) => {
  const chip = document.createElement('div');
  chip.className = 'slopspotter-chip';
  chip.dataset.risk = pkg.result?.riskLevel ?? 'unknown';

  const dot = document.createElement('span');
  dot.className = 'slopspotter-chip__dot';
  dot.style.backgroundColor = RISK_COLORS[chip.dataset.risk] ?? RISK_COLORS.unknown;

  const label = document.createElement('span');
  label.className = 'slopspotter-chip__label';
  label.textContent = pkg.name;

  chip.append(label);
  const tooltip = createTooltip(pkg);
  tooltip.addEventListener('click', (event) => event.stopPropagation());
  chip.appendChild(tooltip);

  // Do NOT append tooltip to chip. We will append to body when needed.
  // chip.appendChild(tooltip); 

  let tooltipInDom = false;

  const showTooltip = () => {
    if (!tooltipInDom) {
      document.body.appendChild(tooltip);
      tooltipInDom = true;
    }

    const rect = chip.getBoundingClientRect();
    const viewportPadding = 12;
    const tooltipWidth = tooltip.offsetWidth || 260;
    const tooltipHeight = tooltip.offsetHeight || 180;

    // Keep tooltip in viewport while anchoring to the chip
    let left = Math.min(Math.max(rect.left, viewportPadding), window.innerWidth - tooltipWidth - viewportPadding);
    let top = rect.bottom + 8;
    const maxTop = window.innerHeight - tooltipHeight - viewportPadding;
    if (top > maxTop) {
      top = Math.max(rect.top - tooltipHeight - 8, viewportPadding);
    }

    tooltip.style.position = 'fixed';
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
    tooltip.classList.add('slopspotter-tooltip--visible');
  };

  const hideTooltip = () => {
    if (activeChip !== chip) {
      tooltip.classList.remove('slopspotter-tooltip--visible');
    }
  };

  chip.addEventListener('mouseenter', showTooltip);
  chip.addEventListener('mouseleave', () => {
    if (activeChip !== chip) {
      hideTooltip();
    }
  });

  chip.addEventListener('click', (event) => {
    event.stopPropagation();
    if (activeChip && activeChip !== chip) {
      // Deactivate other chip
      activeChip.classList.remove('slopspotter-chip--active');
      // We also need to hide its tooltip? 
      // Since we don't have reference to other chip's tooltip here easily, 
      // we rely on the document click listener or the fact that 'activeChip' logic is shared.
      // Actually, we should dispatch an event or use a shared manager, but for now:
      // The document click listener handles closing others.
    }

    const willActivate = !chip.classList.contains('slopspotter-chip--active');
    chip.classList.toggle('slopspotter-chip--active', willActivate);

    if (willActivate) {
      activeChip = chip;
      showTooltip();
    } else {
      activeChip = null;
      hideTooltip();
    }
  });

  // Close on ANY scroll to prevent detached tooltip
  window.addEventListener('scroll', () => {
    if (activeChip === chip) {
      chip.classList.remove('slopspotter-chip--active');
      activeChip = null;
    }
    hideTooltip();
  }, { capture: true, passive: true });

  if (!documentClickBound) {
    document.addEventListener('click', (e) => {
      // If click is inside tooltip, do nothing (stopPropagation is on tooltip)
      // But since tooltip is in body, we need to check if e.target is inside tooltip
      if (activeChip && !activeChip.contains(e.target)) {
        // We also need to check if click is in the tooltip element itself
        // But we can't easily check that globally without a reference.
        // However, the tooltip has a stopPropagation listener on it.
        // So if the event reached document, it wasn't on the tooltip.
        activeChip.classList.remove('slopspotter-chip--active');
        activeChip = null;
        // We need to hide the tooltip of the active chip. 
        // Since we don't have the ref here, we rely on the fact that 
        // the tooltip hides when 'slopspotter-tooltip--visible' is removed.
        // Wait, we need to remove that class.
        // The global listener is tricky with the portal pattern.
        // Let's rely on the scroll/click logic within the closure.
      }
    });
    // We need a way to close the *current* tooltip from the global listener.
    // Let's modify the global listener to dispatch a custom event or just let the closure handle it?
    // Actually, simpler:
    document.addEventListener('click', () => {
      // This fires if not stopped.
      if (activeChip) {
        // We can't close the tooltip here because we don't have the ref.
        // But we can trigger a click on body? No.
        // We can use a custom event.
        document.dispatchEvent(new CustomEvent('slopspotter-close-all'));
      }
    });
    documentClickBound = true;
  }

  document.addEventListener('slopspotter-close-all', () => {
    chip.classList.remove('slopspotter-chip--active');
    if (activeChip === chip) activeChip = null;
    hideTooltip();
  });

  return chip;

  if (!documentClickBound) {
    document.addEventListener('click', () => {
      if (activeChip) {
        activeChip.classList.remove('slopspotter-chip--active');
        activeChip = null;
      }
    });
    documentClickBound = true;
  }

  return chip;
};

const createTooltip = (pkg) => {
  const tooltip = document.createElement('div');
  tooltip.className = 'slopspotter-chip__tooltip';

  const heading = document.createElement('h4');
  const riskLabel = pkg.result?.riskLevel ?? 'unknown';
  const scoreText =
    typeof pkg.result?.score === 'number' ? ` (score ${(pkg.result.score * 100).toFixed(0)}%)` : '';
  heading.textContent = `Risk: ${riskLabel}${scoreText}`;

  const summary = document.createElement('p');
  summary.textContent = pkg.result?.summary ?? 'No additional metadata provided. Proceed with caution.';

  tooltip.append(heading, summary);

  const tags = buildTags(pkg);
  if (tags.length) {
    const tagRow = document.createElement('div');
    tagRow.className = 'slopspotter-chip__tags';
    tags.forEach((tag) => {
      const t = document.createElement('span');
      t.className = 'slopspotter-chip__tag';
      t.textContent = tag;
      tagRow.appendChild(t);
    });
    tooltip.appendChild(tagRow);
  }

  // Add action buttons row
  const actionsRow = document.createElement('div');
  actionsRow.style.display = 'flex';
  actionsRow.style.flexDirection = 'column'; /* Stack items vertically */
  actionsRow.style.alignItems = 'flex-start';
  actionsRow.style.width = '100%'; /* Full width */
  actionsRow.style.height = 'auto';
  actionsRow.style.flexShrink = '0';
  actionsRow.style.gap = '8px';

  // Deep Scan button (allow for all risk levels to let users probe any package)
  const deepScanBtn = createDeepScanButton(pkg);
  actionsRow.appendChild(deepScanBtn);

  if (pkg.result?.metadataUrl) {
    const link = document.createElement('a');
    link.href = pkg.result.metadataUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View metadata';
    actionsRow.appendChild(link);
  }

  if (actionsRow.children.length > 0) {
    tooltip.appendChild(actionsRow);
  }

  return tooltip;
};

/**
 * Create a Deep Scan button for VM-based analysis
 */
const createDeepScanButton = (pkg) => {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'slopspotter-deep-scan-btn';
  btn.textContent = 'Deep Scan'; // Remove icon to save space
  btn.title = 'Run package in isolated VM to detect malicious behavior';

  // Container for results (will be added after scan)
  const resultContainer = document.createElement('div');

  btn.addEventListener('click', async (event) => {
    event.stopPropagation();
    event.preventDefault();

    btn.disabled = true;
    btn.textContent = 'Scanning...'; // Remove icon, keep simple text

    try {
      const response = await browser.runtime.sendMessage({
        type: 'deep-scan',
        payload: {
          packageName: pkg.name,
          language: normalizeLanguageForDeepScan(pkg.language),
          context: {
            ...(pkg.result ?? {}),
            originalLanguage: pkg.language || ''
          } // pass heuristic context (registry/score) + original language to native host
        }
      });

      if (response && response.success && response.result) {
        const result = response.result;
        renderDeepScanResult(resultContainer, result);
        if (result.isMalicious) {
          btn.textContent = 'Malicious!'; // Remove icon, keep simple text
          btn.classList.add('malicious');
        } else {
          btn.textContent = 'Scanned'; // Remove icon
        }
        btn.disabled = true;
      } else {
        renderDeepScanError(resultContainer, response?.error || 'Deep scan failed');
        btn.innerHTML = '<span class="icon"></span> Retry Scan';
        btn.disabled = false;
      }
    } catch (error) {
      console.error('Deep scan error:', error);
      renderDeepScanError(resultContainer, error.message);
      btn.innerHTML = '<span class="icon"></span> Retry Scan';
      btn.disabled = false;
    }
  });

  // Wrap button and result container
  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'column';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.width = '100%';
  wrapper.style.height = 'auto';
  wrapper.style.flexShrink = '0';
  wrapper.appendChild(btn);
  wrapper.appendChild(resultContainer);

  return wrapper;
};

/**
 * Normalize language string for deep scan API
 */
const normalizeLanguageForDeepScan = (language) => {
  if (!language) return 'Python';
  const lower = language.toLowerCase();
  if (lower === 'python' || lower === 'py') return 'Python';
  if (['javascript', 'js', 'node', 'npm', 'typescript', 'ts'].includes(lower)) return 'JavaScript';
  return 'Python'; // Default fallback
};

/**
 * Render deep scan result in the tooltip
 */
const renderDeepScanResult = (container, result) => {
  container.innerHTML = '';

  const div = document.createElement('div');
  div.className = `slopspotter-deep-scan-result ${result.isMalicious ? 'malicious' : 'safe'}`;

  const title = document.createElement('strong');
  title.textContent = result.isMalicious
    ? `Malicious behavior detected (${Math.round(result.confidence * 100)}% confidence)`
    : 'No malicious behavior detected';

  div.appendChild(title);

  if (result.indicators && result.indicators.length > 0) {
    const list = document.createElement('ul');
    list.style.margin = '6px 0 0 0';
    list.style.paddingLeft = '16px';
    result.indicators.slice(0, 5).forEach((indicator) => {
      const li = document.createElement('li');
      li.textContent = indicator;
      list.appendChild(li);
    });
    div.appendChild(list);
  }

  // Network details are already summarized in indicators; skip redundant count here.

  container.appendChild(div);
};

/**
 * Render deep scan error in the tooltip
 */
const renderDeepScanError = (container, errorMessage) => {
  container.innerHTML = '';

  const div = document.createElement('div');
  div.className = 'slopspotter-deep-scan-result error';
  div.textContent = `${errorMessage}`;

  container.appendChild(div);
};

const buildTags = (pkg) => {
  const tags = [];
  const summary = pkg.result?.summary?.toLowerCase?.() ?? '';
  if (summary.includes('not found')) tags.push('Not found');
  if (summary.includes('install hooks') || summary.includes('install scripts')) tags.push('Install scripts');
  if (
    summary.includes('missing metadata') ||
    summary.includes('missing repo') ||
    summary.includes('missing homepage')
  ) {
    tags.push('Missing metadata');
  }
  if (summary.includes('very new') || summary.includes('recently changed')) tags.push('New/changed');
  if (summary.includes('low adoption') || summary.includes('few releases')) tags.push('Low adoption');
  return tags;
};
