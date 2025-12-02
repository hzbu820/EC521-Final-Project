import { describe, expect, it } from 'vitest';
import { extractPackages } from '../src/utils/parser.js';

describe('extractPackages', () => {
  it('detects aliased imports', () => {
    const code = 'import numpy as np';
    const result = extractPackages(code, { language: 'python' });
    expect(result.map((p) => p.name)).toEqual(['numpy']);
  });

  it('deduplicates multiple imports from same module', () => {
    const code = 'from random import randint, choice';
    const result = extractPackages(code, { language: 'python' });
    expect(result.map((p) => p.name)).toEqual(['random']);
  });

  it('captures relative imports by stripping leading dots', () => {
    const code = 'from .utils import helper\nfrom ..common import constants';
    const result = extractPackages(code, { language: 'python' });
    expect(result.map((p) => p.name).sort()).toEqual(['common', 'utils']);
  });

  it('includes stdlib-style imports now that blacklist is relaxed', () => {
    const code = 'import os\nimport sys';
    const result = extractPackages(code, { language: 'python' });
    expect(result.map((p) => p.name).sort()).toEqual(['os', 'sys']);
  });
});
