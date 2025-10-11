/**
 * Find all of the code blocks in the document.
 *
 * @returns {Array<HTMLElement>} Array of code blocks.
 */
function getDocumentCodeBlocks() {
  // Find all HTML tags with <code>
  const codeElements = document.querySelectorAll("code");
  // Find all code elements using highlight.js
  const hljsElements = Array.from(codeElements).filter((node) =>
    node.className.includes("hljs"),
  );
  // Return elements
  if (Array.length > 0) {
    console.log(hljsElements);
    return hljsElements;
  } else {
    return Array(0);
  }
}

/**
 * Use regular expressions to find all of the Python modules imported in a block of text.
 *
 * Ways to import packages in Python:
 *
 * ```python
 * import my_module
 * import my_module as mm
 * import my_module.my_submodule
 * import my_module.my_submodule as mms
 * from my_module import *
 * from my_module import my_submodule
 * from my_module.my_submodule import *
 * from my_module.my_submodule import my_function
 * ```
 *
 * @param {HTMLElement} pythonCodeBlock code block containing Python code.
 * @returns {Array<String>} List of python packages imported by the code block.
 */
function getPythonPackages(pythonCodeBlock) {
  const pythonCode = pythonCodeBlock.textContent;
  // In all cases, we only want to get the `my_module` part of the import statement
  const regex_import = /^import\s+([a-zA-Z_][a-zA-Z0-9_]+)/gm;
  const regex_from = /^from\s([a-zA-Z_][a-zA-Z0-9_]+)(.*)?\s+import/gm;

  const importMatches = pythonCode.matchAll(regex_import);
  const fromMatches = pythonCode.matchAll(regex_from);

  var packages = Array(0);
  for (const match of importMatches) {
    packages.push(match[1]);
  }
  for (const match of fromMatches) {
    packages.push(match[1]);
  }
  return packages;
}

/**
 * Get all of the Python packages imported in the document.
 *
 * @returns {Array<Array<String>>} List of python packages imported by each code block.
 */
function getDocumentPythonPackages() {
  const codeBlocks = getDocumentCodeBlocks();
  var packages = Array(0);
  for (const codeBlock of codeBlocks) {
    packages.push(getPythonPackages(codeBlock));
  }
  console.log("Packages:", packages);
  return packages;
}

// Observe the entire document for changes
const targetNode = document.body;
const config = { childList: true, subtree: true };
const observer = new MutationObserver(getDocumentPythonPackages);
observer.observe(targetNode, config);
