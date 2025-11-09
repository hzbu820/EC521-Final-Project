const RELATIVE_PREFIXES = ['.', '/', '~'];

const PATTERNS = [
  {
    language: 'javascript',
    regex: /import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]/gi
  },
  {
    language: 'javascript',
    regex: /require\(\s*['"]([^'"]+)['"]\s*\)/gi
  },
  {
    language: 'javascript',
    regex: /npm\s+(?:install|i|add)\s+([@\w./-]+)/gi
  },
  {
    language: 'python',
    regex: /(?:from|import)\s+([a-zA-Z0-9_.]+)/gi,
    sanitizer: (name) => name.split('.')[0]
  },
  {
    language: 'python',
    regex: /pip(?:3)?\s+install\s+([a-zA-Z0-9_.-]+)/gi
  },
  {
    language: 'rust',
    regex: /cargo\s+(?:add|install)\s+([a-zA-Z0-9_-]+)/gi
  },
  {
    language: 'go',
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

/**
 * Extract candidate package references from code text.
 * @param {string} code
 * @returns {Array<{name: string, language: string, contextSnippet: string}>}
 */
export const extractPackages = (code) => {
  const seen = new Map();

  for (const { language, regex, sanitizer } of PATTERNS) {
    regex.lastIndex = 0;
    let match;

    while ((match = regex.exec(code)) !== null) {
      const rawName = match[1]?.trim() ?? '';
      const candidate = sanitizer ? sanitizer(rawName) : rawName;
      if (!isLikelyPackageName(candidate)) {
        continue;
      }

      const normalized = candidate.replace(/['"]/g, '');
      if (seen.has(normalized)) {
        continue;
      }

      seen.set(normalized, {
        name: normalized,
        language,
        contextSnippet: buildContextSnippet(code, match.index)
      });
    }
  }

  return Array.from(seen.values());
};
