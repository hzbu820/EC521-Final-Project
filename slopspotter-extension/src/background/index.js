import browser from 'webextension-polyfill';

const DEFAULT_SETTINGS = {
  autoAnnotate: true,
  backendMode: 'http',
  backendBaseUrl: 'http://localhost:8000',
  nativeHostName: 'slopspotter'
};

browser.runtime.onInstalled.addListener(async () => {
  const stored = await getSettings();
  await saveSettings({ ...DEFAULT_SETTINGS, ...stored });
});

browser.runtime.onMessage.addListener(async (message) => {
  if (!message || typeof message !== 'object' || !('type' in message)) {
    return undefined;
  }

  switch (message.type) {
    case 'check-packages':
      return handlePackageCheck(message.payload);
    case 'get-settings':
      return getSettings();
    case 'save-settings':
      await saveSettings(message.payload);
      return { ok: true };
    default:
      return undefined;
  }
});

const handlePackageCheck = async (payload) => {
  const settings = await getSettings();

  try {
    const response =
      settings.backendMode === 'native'
        ? await queryNativeHost(settings.nativeHostName, payload)
        : await queryHttpBackend(settings.backendBaseUrl, payload);
    if (response) {
      return response;
    }
  } catch (error) {
    console.warn('Slopspotter backend request failed, using heuristics fallback', error);
  }

  return {
    snippetId: payload.snippetId,
    packages: payload.packages.map((pkg) => ({
      ...pkg,
      result: buildHeuristicRisk(pkg)
    })),
    warning:
      settings.backendMode === 'native'
        ? 'Native host unreachable. Displaying heuristic risk estimates.'
        : 'Backend unreachable. Displaying heuristic risk estimates.'
  };
};

const queryHttpBackend = async (baseUrl, payload) => {
  if (!baseUrl) {
    return null;
  }

  const endpoint = buildEndpoint(baseUrl, '/check-packages');
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Backend returned status ${response.status}`);
  }

  return response.json();
};

const queryNativeHost = async (hostName, payload) => {
  if (!hostName) {
    return null;
  }

  return browser.runtime.sendNativeMessage(hostName, payload);
};

const buildHeuristicRisk = (pkg) => {
  const normalized = pkg.name.toLowerCase();
  const suspiciousTokens = ['installer', 'updater', 'crypto', 'mining', 'hack', 'typo'];
  const hasSuspiciousToken = suspiciousTokens.some((token) => normalized.includes(token));

  if (hasSuspiciousToken || normalized.length > 18) {
    return {
      riskLevel: 'high',
      score: 0.85,
      summary: 'Name resembles known malicious naming patterns.',
      metadataUrl: registryUrlFor(pkg)
    };
  }

  if (/[0-9]/.test(normalized) || normalized.includes('-')) {
    return {
      riskLevel: 'medium',
      score: 0.55,
      summary: 'Package name includes uncommon characters; verify legitimacy.',
      metadataUrl: registryUrlFor(pkg)
    };
  }

  return {
    riskLevel: 'low',
    score: 0.15,
    summary: 'No immediate red flags detected from heuristic scan.',
    metadataUrl: registryUrlFor(pkg)
  };
};

const registryUrlFor = (pkg) => {
  switch (pkg.language) {
    case 'python':
      return `https://pypi.org/project/${pkg.name}/`;
    case 'javascript':
      return `https://www.npmjs.com/package/${pkg.name}`;
    case 'rust':
      return `https://crates.io/crates/${pkg.name}`;
    case 'go':
      return `https://pkg.go.dev/${pkg.name}`;
    default:
      return undefined;
  }
};

const getSettings = async () => {
  const stored = await browser.storage.sync.get(DEFAULT_SETTINGS);
  return {
    backendMode: stored.backendMode ?? DEFAULT_SETTINGS.backendMode,
    backendBaseUrl: stored.backendBaseUrl ?? DEFAULT_SETTINGS.backendBaseUrl,
    nativeHostName: stored.nativeHostName ?? DEFAULT_SETTINGS.nativeHostName,
    autoAnnotate: stored.autoAnnotate ?? DEFAULT_SETTINGS.autoAnnotate
  };
};

const saveSettings = async (settings) => {
  await browser.storage.sync.set(settings);
};

const buildEndpoint = (baseUrl, path) => {
  try {
    const url = new URL(path, baseUrl);
    return url.toString();
  } catch (error) {
    console.warn('Slopspotter: invalid backend URL configured', error);
    return path;
  }
};
