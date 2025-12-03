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
}

.slopspotter-chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 6px 10px;
  border-radius: 9999px;
  color: #0f172a;
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.18), rgba(148, 163, 184, 0.08));
  border: 1.5px solid rgba(148, 163, 184, 0.45);
  cursor: default;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35), 0 4px 10px rgba(15, 23, 42, 0.08);
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  z-index: 2147483645;
}

.slopspotter-chip:hover,
.slopspotter-chip:focus-visible {
  transform: translateY(-1px);
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
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 230px;
  max-width: 300px;
  padding: 12px 14px;
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

.slopspotter-chip:hover .slopspotter-chip__tooltip,
.slopspotter-chip:focus-within .slopspotter-chip__tooltip,
.slopspotter-chip.slopspotter-chip--active .slopspotter-chip__tooltip {
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
  if (document.getElementById(STYLE_ID)) {
    return;
  }

  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = STYLE_CONTENT;
  document.head?.appendChild(style);
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

  chip.append(dot, label);
  const tooltip = createTooltip(pkg);
  tooltip.addEventListener('click', (event) => event.stopPropagation());
  chip.appendChild(tooltip);

  chip.addEventListener('click', (event) => {
    event.stopPropagation();
    if (activeChip && activeChip !== chip) {
      activeChip.classList.remove('slopspotter-chip--active');
    }
    const willActivate = !chip.classList.contains('slopspotter-chip--active');
    chip.classList.toggle('slopspotter-chip--active', willActivate);
    activeChip = willActivate ? chip : null;
  });

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

  if (pkg.result?.metadataUrl) {
    const link = document.createElement('a');
    link.href = pkg.result.metadataUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View metadata';
    tooltip.appendChild(link);
  }

  return tooltip;
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
