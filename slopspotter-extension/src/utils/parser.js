/*
Table of Contents
- Language normalization helpers
- Regex patterns per language
- Helpers: context snippet, blacklist, validators
- extractPackages: main exported API
*/

// Disallow paths/URLs that look like local files or protocol targets.
const RELATIVE_PREFIXES = ['.', '/', '~'];
// Identifiers we should ignore per language (kept intentionally small).
const COMMON_IDENTIFIER_BLACKLIST = {
  python: new Set([]),
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

// Patterns that extract candidate package names from code by language.
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
    regex: /from\s+(\.*[a-zA-Z0-9_.]+)/gi,
    sanitizer: (name) => name.replace(/^\.+/, '').split('.')[0]
  },
  {
    languages: ['python'],
    regex: /\bimport\s+(\.*[a-zA-Z0-9_.]+)/gi,
    sanitizer: (name) => name.replace(/^\.+/, '').split('.')[0],
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
  },
  {
    languages: ['go'],
    // Handles import "fmt" and import alias "io/ioutil"
    regex: /import\s+"([^"]+)"/gi
  },
  {
    languages: ['go'],
    // Handles grouped imports: import ("fmt"\n "net/http")
    regex: /import\s*\(\s*([\s\S]*?)\)/gi,
    sanitizer: (block) => {
      const matches = [];
      const inner = block || '';
      const re = /"([^"]+)"/g;
      let m;
      while ((m = re.exec(inner)) !== null) {
        matches.push(m[1]);
      }
      return matches;
    }
  },
  {
    languages: ['rust'],
    // Handles `use crate::...;` and `use std::fs;`
    regex: /\buse\s+([a-zA-Z0-9_]+)::/gi,
    sanitizer: (name) => name
  },
  {
    languages: ['rust', 'toml'],
    // Cargo.toml style dependencies: rand = "0.9"
    regex: /^\s*([a-zA-Z0-9_-]+)\s*=\s*"[^"]+"/gim
  },
  {
    languages: ['rust'],
    // Inline crate path references: rand::thread_rng()
    regex: /\b([a-zA-Z0-9_]+)::[a-zA-Z0-9_]+/gi
  }
];

const isLikelyPackageName = (value) => {
  // Basic sanity checks: non-empty, not a path/URL.
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
  // Grab a short slice of code around the match for diagnostics.
  const start = Math.max(0, index - 40);
  const end = Math.min(code.length, index + 60);
  return code.slice(start, end).replace(/\s+/g, ' ').trim();
};

const isPartOfFromStatement = (code, index) => {
  // Detects whether an "import X" is actually part of "from Y import X".
  const windowStart = Math.max(0, index - 30);
  const snippet = code
    .slice(windowStart, index)
    .replace(/\s+/g, ' ')
    .toLowerCase();
  return /\bfrom\s+[a-z0-9_.]+\s*$/.test(snippet);
};

const isBlacklisted = (language, name) => {
  // Skip common identifiers that are unlikely to be packages.
  const normalized = name.toLowerCase();
  const blacklist = COMMON_IDENTIFIER_BLACKLIST[language];
  return blacklist ? blacklist.has(normalized) : false;
};

/**
 * Extract candidate package references from code text.
 * - Parses using regex patterns per language.
 * - De-duplicates by name.
 * - Applies simple sanity checks and optional language hint.
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

      const candidateRaw = sanitizer ? sanitizer(rawName, { code, match }) : rawName;
      const candidates = Array.isArray(candidateRaw) ? candidateRaw : [candidateRaw];

      for (const cand of candidates) {
        if (!isLikelyPackageName(cand)) {
          continue;
        }
        const normalizedName = cand.replace(/['"]/g, '');
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
  }

  return Array.from(seen.values());
};
