const RELATIVE_PREFIXES = ['.', '/', '~'];
const COMMON_IDENTIFIER_BLACKLIST = {
  python: new Set(['array', 'string', 'path', 'datetime', 'sys', 'os']),
  javascript: new Set(['string', 'number'])
};

const LANGUAGE_ALIASES = {
  javascript: 'javascript',
  js: 'javascript',
  node: 'javascript',
  nodejs: 'javascript',
  typescript: 'typescript',
  ts: 'typescript',
  py: 'python',
  python: 'python',
  golang: 'go',
  go: 'go',
  rust: 'rust',
  sh: 'shell',
  bash: 'shell',
  shell: 'shell'
};

export const normalizeLanguage = (value = '') => {
  if (value === undefined || value === null) {
    return undefined;
  }
  const cleaned = value.toString().trim().toLowerCase();
  if (!cleaned) {
    return undefined;
  }
  return LANGUAGE_ALIASES[cleaned] ?? cleaned;
};

const PATTERNS = [
  {
    languages: ['javascript', 'typescript'],
    regex: /import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]/gi
  },
  {
    languages: ['javascript', 'typescript'],
    regex: /require\(\s*['"]([^'"]+)['"]\s*\)/gi
  },
  {
    languages: ['javascript', 'typescript'],
    regex: /npm\s+(?:install|i|add)\s+([@\w./-]+)/gi
  },
  {
    languages: ['python'],
    regex: /from\s+([a-zA-Z0-9_.]+)/gi,
    sanitizer: (name) => name.split('.')[0]
  },
  {
    languages: ['python'],
    regex: /\bimport\s+([a-zA-Z0-9_.]+)/gi,
    sanitizer: (name) => name.split('.')[0],
    validator: ({ code, index }) => !isPartOfFromStatement(code, index)
  },
  {
    languages: ['python'],
    regex: /pip(?:3)?\s+install\s+([a-zA-Z0-9_.-]+)/gi
  },
  {
    languages: ['rust'],
    regex: /cargo\s+(?:add|install)\s+([a-zA-Z0-9_-]+)/gi
  },
  {
    languages: ['go'],
    regex: /go\s+get\s+([a-zA-Z0-9_.-/]+)/gi
  }
];

const isLikelyPackageName = (value) => {
  if (!value) {
    return false;
  }

  const trimmed = value.trim();
  if (trimmed.length < 2) {
    return false;
  }

  const lowered = trimmed.toLowerCase();
  if (RELATIVE_PREFIXES.some((prefix) => lowered.startsWith(prefix))) {
    return false;
  }

  if (lowered.startsWith('http://') || lowered.startsWith('https://')) {
    return false;
  }

  return true;
};

const buildContextSnippet = (code, index) => {
  const start = Math.max(0, index - 40);
  const end = Math.min(code.length, index + 60);
  return code.slice(start, end).replace(/\s+/g, ' ').trim();
};

const isPartOfFromStatement = (code, index) => {
  const windowStart = Math.max(0, index - 30);
  const snippet = code
    .slice(windowStart, index)
    .replace(/\s+/g, ' ')
    .toLowerCase();
  return /\bfrom\s+[a-z0-9_.]+\s*$/.test(snippet);
};

const isBlacklisted = (language, name) => {
  const normalized = name.toLowerCase();
  const blacklist = COMMON_IDENTIFIER_BLACKLIST[language];
  return blacklist ? blacklist.has(normalized) : false;
};

/**
 * Extract candidate package references from code text.
 * @param {string} code
 * @param {{language?: string}} options
 * @returns {Array<{name: string, language: string, contextSnippet: string}>}
 */
export const extractPackages = (code, options = {}) => {
  const seen = new Map();
  const normalizedLanguage = normalizeLanguage(options.language);
  const candidatePatterns = PATTERNS.filter(({ languages }) =>
    normalizedLanguage ? languages.includes(normalizedLanguage) : true
  );
  const patternsToRun = candidatePatterns.length > 0 ? candidatePatterns : PATTERNS;

  for (const pattern of patternsToRun) {
    const { regex, sanitizer, validator } = pattern;
    regex.lastIndex = 0;
    let match;

    while ((match = regex.exec(code)) !== null) {
      const rawName = match[1]?.trim() ?? '';
      if (!rawName) {
        continue;
      }

      if (validator && !validator({ code, index: match.index, match })) {
        continue;
      }

      const candidate = sanitizer ? sanitizer(rawName, { code, match }) : rawName;
      if (!isLikelyPackageName(candidate)) {
        continue;
      }

      const normalizedName = candidate.replace(/['"]/g, '');
      const languageForMatch = normalizedLanguage ?? pattern.languages[0];
      if (isBlacklisted(languageForMatch, normalizedName)) {
        continue;
      }

      if (seen.has(normalizedName)) {
        continue;
      }

      seen.set(normalizedName, {
        name: normalizedName,
        language: languageForMatch,
        contextSnippet: buildContextSnippet(code, match.index)
      });
    }
  }

  return Array.from(seen.values());
};
