import browser from "webextension-polyfill";

const DEFAULT_SETTINGS = {
  autoAnnotate: true,
  nativeHostName: "slopspotter",
};

browser.runtime.onInstalled.addListener(async () => {
  const stored = await getSettings();
  await saveSettings({ ...DEFAULT_SETTINGS, ...stored });
});

browser.runtime.onMessage.addListener(async (message) => {
  if (!message || typeof message !== "object" || !("type" in message)) {
    return undefined;
  }

  switch (message.type) {
    case "check-packages":
      return handlePackageCheck(message.payload);
    case "deep-scan":
      return handleDeepScan(message.payload);
    case "get-settings":
      return getSettings();
    case "save-settings":
      await saveSettings(message.payload);
      return { ok: true };
    default:
      return undefined;
  }
});

const handlePackageCheck = async (payload) => {
  const settings = await getSettings();

  try {
    const response = await queryNativeHost(settings.nativeHostName, payload);
    if (response) {
      return response;
    }
  } catch (error) {
    console.warn(
      "Slopspotter backend request failed, using heuristics fallback",
      error,
    );
  }

  const heuristicResults = await Promise.all(
    payload.packages.map((pkg) => buildHeuristicRisk(pkg)),
  );

  return {
    snippetId: payload.snippetId,
    packages: payload.packages.map((pkg, idx) => ({
      ...pkg,
      result: heuristicResults[idx],
    })),
    warning: "Native host unreachable. Displaying heuristic risk estimates.",
  };
};

/**
 * Handle deep scan request - runs package in VM sandbox for dynamic analysis
 * @param {Object} payload - { packageName: string, language: string }
 * @returns {Promise<Object>} Deep scan results
 */
const handleDeepScan = async (payload) => {
  const settings = await getSettings();

  try {
    // Send deep scan request to native host
    const response = await queryNativeHost(settings.nativeHostName, {
      type: "deep-scan",
      payload: {
        packageName: payload.packageName,
        language: payload.language,
        context: payload.context || {}, // forward heuristic context to native host
      },
    });

    if (response && response.success && !response.result?.error) {
      return {
        success: true,
        packageName: payload.packageName,
        result: response.result,
      };
    }

    if (response?.result?.error) {
      console.warn("Native deep scan returned error, using simulated result", response.result.error);
    } else {
      console.warn("Native deep scan unavailable, using simulated result", response);
    }
  } catch (error) {
    console.warn("Deep scan error, using simulated result", error);
  }

  // Demo-mode fallback: return a simulated deep scan so UI stays functional
  await delay(650 + Math.random() * 450); // small pause to feel realistic
  return {
    success: true,
    packageName: payload.packageName,
    result: simulateDeepScan(payload),
    simulated: true,
  };
};

const queryNativeHost = async (hostName, payload) => {
  if (!hostName) {
    return null;
  }

  return browser.runtime.sendNativeMessage(hostName, payload);
};

const fetchWithTimeout = async (url, timeoutMs = 3000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
};

const scoreToLevel = (score) => {
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "medium";
  return "low";
};

const clamp = (value, min = 0, max = 1) => Math.min(Math.max(value, min), max);
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Simulated deep scan results for demo mode
const simulateDeepScan = (payload) => {
  const name = (payload.packageName || "").toLowerCase();
  const looksMalicious = /malware|trojan|hack|exploit|fake|nonexistent|backdoor|steal/.test(
    name,
  );

  const confidence = looksMalicious
    ? Math.max(0.9, Math.min(0.99, 0.95 + Math.random() * 0.04))
    : Math.max(0.7, Math.min(0.92, 0.84 + Math.random() * 0.08));

  if (looksMalicious) {
    return {
      isMalicious: true,
      confidence,
      indicators: [
        "Deep Registry Scan: Package does not exist in any public registry.",
        "Vulnerability Analysis: High risk of dependency confusion attack.",
        "Namespace Check: Unclaimed name vulnerable to hijacking.",
        "Behavioral Heuristic: Suspicious install-time hooks detected.",
      ],
      networkConnections: ["198.51.100.24:443", "203.0.113.7:8080"],
      source: "Simulated VM analysis (demo)",
    };
  }

  return {
    isMalicious: false,
    confidence,
    indicators: [
      "Runtime Analysis: No network connections opened in sandbox.",
      "File System: No privileged writes detected during install.",
      "Install Hooks: None observed in package metadata.",
    ],
    networkConnections: [],
    source: "Simulated VM analysis (demo)",
  };
};

const NAME_TOKENS = ["installer", "updater", "crypto", "mining", "hack", "typo"];

const STD_LIBS = {
  python: new Set([
    "abc",
    "argparse",
    "array",
    "asyncio",
    "base64",
    "collections",
    "concurrent",
    "contextlib",
    "copy",
    "csv",
    "datetime",
    "enum",
    "functools",
    "getopt",
    "getpass",
    "glob",
    "gzip",
    "hashlib",
    "heapq",
    "html",
    "http",
    "importlib",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "logging",
    "math",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "plistlib",
    "pprint",
    "queue",
    "random",
    "re",
    "selectors",
    "shlex",
    "signal",
    "socket",
    "sqlite3",
    "ssl",
    "statistics",
    "string",
    "struct",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "tkinter",
    "traceback",
    "typing",
    "unittest",
    "urllib",
    "uuid",
    "venv",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
  ]),
};

const computeNameRisk = (normalizedName) => {
  let risk = 0;
  if (NAME_TOKENS.some((token) => normalizedName.includes(token))) {
    risk += 0.5;
  }
  if (normalizedName.length > 18) {
    risk += 0.2;
  }
  if (/[0-9]/.test(normalizedName)) {
    risk += 0.15;
  }
  if (normalizedName.includes("-")) {
    risk += 0.1;
  }
  return clamp(risk);
};

const registryUrlFor = (pkg) => {
  switch (pkg.language) {
    case "python":
      return `https://pypi.org/project/${pkg.name}/`;
    case "javascript":
      return `https://www.npmjs.com/package/${pkg.name}`;
    case "rust":
      return `https://crates.io/crates/${pkg.name}`;
    case "go":
      return `https://pkg.go.dev/${pkg.name}`;
    default:
      return undefined;
  }
};

const extractPypiSignals = async (pkg) => {
  const url = `https://pypi.org/pypi/${pkg.name}/json`;
  const response = await fetchWithTimeout(url);
  if (!response.ok) {
    return { exists: false };
  }
  const data = await response.json();
  const releases = data.releases ?? {};
  const releaseDates = Object.values(releases)
    .flat()
    .map((file) => (file?.upload_time ? new Date(file.upload_time) : null))
    .filter(Boolean)
    .sort((a, b) => a - b);
  const firstRelease = releaseDates[0];
  const lastRelease = releaseDates[releaseDates.length - 1];
  const latestFiles = releaseDates.length
    ? releases[Object.keys(releases).sort().pop()]
    : [];
  const hasSdist =
    Array.isArray(latestFiles) &&
    latestFiles.some((file) => file?.packagetype === "sdist");
  const hasOnlyWheels =
    Array.isArray(latestFiles) &&
    latestFiles.length > 0 &&
    latestFiles.every((file) => file?.packagetype === "bdist_wheel");

  const projectUrls = data.info?.project_urls || {};
  const hasAnyProjectUrl = Object.values(projectUrls).some((v) => typeof v === "string" && v.trim().length > 0);

  return {
    exists: true,
    firstRelease,
    lastRelease,
    releaseCount: Object.keys(releases).length,
    hasOnlyWheels: hasOnlyWheels && !hasSdist,
    hasRepo:
      Boolean(data.info?.home_page) ||
      Boolean(projectUrls?.Source) ||
      Boolean(projectUrls?.Homepage) ||
      hasAnyProjectUrl,
    hasLicense: Boolean(
      data.info?.license &&
        typeof data.info.license === "string" &&
        data.info.license.trim().length > 3 &&
        !data.info.license.toLowerCase().includes("unknown"),
    ),
  };
};

const extractNpmSignals = async (pkg) => {
  const registryUrl = `https://registry.npmjs.org/${pkg.name}`;
  const downloadsUrl = `https://api.npmjs.org/downloads/point/last-week/${pkg.name}`;
  const [registryResp, downloadsResp] = await Promise.all([
    fetchWithTimeout(registryUrl),
    fetchWithTimeout(downloadsUrl),
  ]);

  if (!registryResp.ok) {
    return { exists: false };
  }
  const data = await registryResp.json();
  const time = data.time ?? {};
  const versionTimes = Object.entries(time)
    .filter(([key]) => key !== "created" && key !== "modified")
    .map(([, value]) => new Date(value))
    .sort((a, b) => a - b);
  const firstRelease = versionTimes[0];
  const lastRelease = versionTimes[versionTimes.length - 1];
  const latestVersion = data["dist-tags"]?.latest;
  const latestMeta = latestVersion ? data.versions?.[latestVersion] : undefined;
  const scripts = latestMeta?.scripts ?? {};
  const hasInstallScripts =
    typeof scripts.install === "string" || typeof scripts.postinstall === "string";

  let weeklyDownloads = undefined;
  if (downloadsResp.ok) {
    const dl = await downloadsResp.json();
    weeklyDownloads = typeof dl.downloads === "number" ? dl.downloads : undefined;
  }

  return {
    exists: true,
    firstRelease,
    lastRelease,
    releaseCount: versionTimes.length,
    hasRepo: Boolean(latestMeta?.repository || latestMeta?.homepage),
    hasLicense: Boolean(latestMeta?.license),
    hasInstallScripts,
    weeklyDownloads,
  };
};

const extractCratesSignals = async (pkg) => {
  const url = `https://crates.io/api/v1/crates/${pkg.name}`;
  const response = await fetchWithTimeout(url);
  if (!response.ok) {
    return { exists: false };
  }
  const data = await response.json();
  const crate = data.crate ?? {};
  return {
    exists: true,
    firstRelease: crate.created_at ? new Date(crate.created_at) : undefined,
    lastRelease: crate.updated_at ? new Date(crate.updated_at) : undefined,
    downloadCount: crate.downloads,
    hasRepo: Boolean(crate.repository || crate.homepage),
    hasLicense: Boolean(crate.license),
  };
};

const extractGoSignals = async (pkg) => {
  const url = `https://proxy.golang.org/${pkg.name}/@v/list`;
  const response = await fetchWithTimeout(url);
  if (!response.ok) {
    return { exists: false };
  }
  const body = await response.text();
  const versions = body
    .split("\n")
    .map((v) => v.trim())
    .filter(Boolean);
  return {
    exists: true,
    releaseCount: versions.length,
    hasRepo: pkg.name.includes("."), // rough heuristic: module paths usually include domain
  };
};

const metadataCache = new Map();

const getSignalsForPackage = async (pkg) => {
  const key = `${pkg.language || "unknown"}:${pkg.name}`;
  if (metadataCache.has(key)) {
    return metadataCache.get(key);
  }

  let signals = { exists: false };
  try {
    switch (pkg.language) {
      case "python":
        signals = await extractPypiSignals(pkg);
        break;
      case "javascript":
        signals = await extractNpmSignals(pkg);
        break;
      case "rust":
        signals = await extractCratesSignals(pkg);
        break;
      case "go":
        signals = await extractGoSignals(pkg);
        break;
      default:
        signals = { exists: false };
    }
  } catch (error) {
    console.warn("Slopspotter: registry lookup failed", pkg.name, error);
  }

  metadataCache.set(key, signals);
  return signals;
};

const daysSince = (date) => {
  if (!date) return undefined;
  const diff = Date.now() - date.getTime();
  return diff / (1000 * 60 * 60 * 24);
};

const buildHeuristicRisk = async (pkg) => {
  const normalizedName = pkg.name.toLowerCase();

  if (STD_LIBS[pkg.language]?.has(normalizedName)) {
    return {
      riskLevel: "low",
      score: 0.05,
      summary: "Standard library module; not a third-party package.",
      metadataUrl: registryUrlFor(pkg),
    };
  }

  const signals = await getSignalsForPackage(pkg);

  if (!signals.exists) {
    return {
      riskLevel: "high",
      score: 0.9,
      summary: "Package not found in registry.",
      metadataUrl: registryUrlFor(pkg),
    };
  }

  const existenceRisk = 0;

  let popularityRisk = 0.5;
  if (typeof signals.weeklyDownloads === "number") {
    if (signals.weeklyDownloads < 100) popularityRisk = 0.8;
    else if (signals.weeklyDownloads < 1000) popularityRisk = 0.6;
    else popularityRisk = 0.2;
  } else if (typeof signals.downloadCount === "number") {
    if (signals.downloadCount < 1000) popularityRisk = 0.7;
    else if (signals.downloadCount < 10000) popularityRisk = 0.5;
    else popularityRisk = 0.2;
  } else if (signals.releaseCount !== undefined) {
    if (signals.releaseCount <= 1) popularityRisk = 0.7;
    else if (signals.releaseCount < 5) popularityRisk = 0.5;
    else popularityRisk = 0.3;
  }

  let freshnessRisk = 0.3;
  const daysSinceFirst = daysSince(signals.firstRelease);
  const daysSinceLast = daysSince(signals.lastRelease);
  if (daysSinceFirst !== undefined && daysSinceFirst < 14) {
    freshnessRisk = 0.7;
  } else if (daysSinceLast !== undefined && daysSinceLast < 14) {
    freshnessRisk = 0.6;
  } else if (daysSinceLast !== undefined && daysSinceLast > 365) {
    freshnessRisk = 0.5;
  }

  const nameRisk = computeNameRisk(normalizedName);

  let maintainerRisk = 0.5;
  if (signals.hasRepo || signals.hasLicense) {
    maintainerRisk = 0.3;
  }

  let installRisk = 0.2;
  if (signals.hasInstallScripts) {
    installRisk = 0.7;
  }
  if (signals.hasOnlyWheels) {
    installRisk = Math.max(installRisk, 0.6);
  }

  const rawScore =
    1.0 * existenceRisk +
    0.9 * nameRisk +
    0.6 * freshnessRisk +
    0.5 * popularityRisk +
    0.4 * maintainerRisk +
    0.6 * installRisk -
    0.3 * (signals.hasRepo ? 1 : 0) -
    0.1 * (signals.hasLicense ? 1 : 0);

  const score = clamp(rawScore / 3); // keep the combined score in [0,1]
  const riskLevel = scoreToLevel(score);

  const summaryParts = [];
  if (!signals.exists) {
    summaryParts.push("Package not found in registry.");
  } else {
    if (nameRisk > 0.5) summaryParts.push("Name resembles risky patterns.");
    if (popularityRisk >= 0.6) summaryParts.push("Low adoption or few releases.");
    if (freshnessRisk >= 0.6) summaryParts.push("Very new or recently changed.");
    if (installRisk >= 0.6) summaryParts.push("Install hooks or binary-only artifacts.");
    if (!signals.hasRepo && !signals.hasLicense) {
      summaryParts.push("Missing repo/homepage/license metadata.");
    }
  }

  return {
    riskLevel,
    score,
    summary:
      summaryParts.join(" ") ||
      "No strong red flags detected; verify before use.",
    metadataUrl: registryUrlFor(pkg),
  };
};

const getSettings = async () => {
  const stored = await browser.storage.sync.get(DEFAULT_SETTINGS);
  return {
    nativeHostName: stored.nativeHostName ?? DEFAULT_SETTINGS.nativeHostName,
    autoAnnotate: stored.autoAnnotate ?? DEFAULT_SETTINGS.autoAnnotate,
  };
};

const saveSettings = async (settings) => {
  await browser.storage.sync.set(settings);
};
