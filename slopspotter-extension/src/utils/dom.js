const STYLE_ID = 'slopspotter-style';

const STYLE_CONTENT = `
.slopspotter-indicators {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 12px;
  margin-bottom: 6px;
}

.slopspotter-chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px 4px 8px;
  border-radius: 9999px;
  color: #0f172a;
  background: rgba(148, 163, 184, 0.2);
  border: 1px solid rgba(148, 163, 184, 0.35);
  cursor: default;
}

.slopspotter-chip[data-risk="low"] {
  border-color: rgba(34, 197, 94, 0.4);
  background: rgba(34, 197, 94, 0.15);
}

.slopspotter-chip[data-risk="medium"] {
  border-color: rgba(234, 179, 8, 0.5);
  background: rgba(234, 179, 8, 0.15);
}

.slopspotter-chip[data-risk="high"] {
  border-color: rgba(248, 113, 113, 0.55);
  background: rgba(248, 113, 113, 0.18);
}

.slopspotter-chip__dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.slopspotter-chip__label {
  font-weight: 600;
  color: inherit;
}

.slopspotter-chip__tooltip {
  display: none;
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 220px;
  max-width: 280px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #0f172a;
  color: #f8fafc;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  z-index: 2147483646;
}

.slopspotter-chip:hover .slopspotter-chip__tooltip,
.slopspotter-chip:focus-within .slopspotter-chip__tooltip {
  display: block;
}

.slopspotter-chip__tooltip h4 {
  margin: 0 0 6px 0;
  font-size: 13px;
}

.slopspotter-chip__tooltip p {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
}

.slopspotter-chip__tooltip a {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: #38bdf8;
  text-decoration: underline;
}

.slopspotter-warning {
  font-size: 11px;
  background: rgba(234, 179, 8, 0.15);
  border: 1px solid rgba(234, 179, 8, 0.4);
  padding: 6px 10px;
  border-radius: 8px;
  color: #854d0e;
}

.slopspotter-action-button {
  appearance: none;
  border: 1px solid rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.15);
  color: #1d4ed8;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 9999px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s ease-in-out, color 0.2s ease-in-out;
}

.slopspotter-action-button:hover {
  background: rgba(59, 130, 246, 0.25);
}

.slopspotter-action-button:disabled {
  opacity: 0.6;
  cursor: progress;
}
`;

const RISK_COLORS = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#ef4444',
  unknown: '#94a3b8'
};

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
  const existing = parent.querySelector(':scope > .slopspotter-indicators');
  if (existing) {
    return existing;
  }

  const container = document.createElement('div');
  container.className = 'slopspotter-indicators';
  parent.insertBefore(container, snippetElement);
  return container;
};

export const renderPending = (snippetElement, message = 'Slopspotter is checking packages...') => {
  const container = getIndicatorContainer(snippetElement);
  container.replaceChildren();

  const pending = document.createElement('div');
  pending.className = 'slopspotter-warning';
  pending.textContent = message;
  container.appendChild(pending);
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
  chip.appendChild(createTooltip(pkg));

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
