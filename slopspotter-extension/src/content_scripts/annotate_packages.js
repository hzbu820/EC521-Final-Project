/**
 * Get the JSON metadata of a package from its name on the Python Package Index (PyPI).
 *
 * @param {string} packageName
 * @returns {Promise<any>}
 */
async function queryPyPI(packageName) {
  const url = `https://pypi.org/pypi/${packageName}/json`;
  try {
    const response = await fetch(url);

    // Check if the response was successful (status code 200-299)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Package "${packageName}" not found on PyPI.`);
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
}

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
  if (hljsElements.length > 0) {
    console.log(hljsElements);
  }
  return hljsElements;
}

/**
 * Find all of the `<pre>` blocks in the document.
 *
 * @returns {Array<HTMLElement>} Array of pre-formatted blocks.
 */
function getDocumentPreBlocks() {
  // Find all HTML tags with <code>
  const preElements = document.querySelectorAll("pre");
  return Array.from(preElements);
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

  var packages = [];
  for (const match of importMatches) {
    packages.push(match[1]);
  }
  for (const match of fromMatches) {
    packages.push(match[1]);
  }
  console.log("Found:", packages);
  return packages;
}

/**
 * @param {Object.<string, Object>} packageInfo
 * @returns {string}
 */
function FormatPyPIInfo(packageInfo) {
  const a = `${packageInfo.info.name}\n`;
  const b = `Latest Version: ${packageInfo.info.version}\n`;
  const c = `Summary: ${packageInfo.info.summary}\n`;
  const d = `Project URL: ${packageInfo.info.project_url}`;
  return a + b + c + d;
}

/**
 * Add a `title` to every code block's parent element in the document listing its packages.
 */
function annotateCodeBlocks() {
  const codeBlocks = getDocumentCodeBlocks();

  for (var codeBlock of codeBlocks) {
    const packages = getPythonPackages(codeBlock);
    if (packages.length > 0) {
      var responses = packages.map(queryPyPI);
      Promise.all(responses).then((values) => {
        var summaries = values.map(FormatPyPIInfo);
        console.log("Changed");
        codeBlock.parentElement.title = summaries.join("\n\n");
      });
    }
  }
}

// Observe the entire document for changes
const targetNode = document.body;
const config = { childList: true, subtree: true };
const observer = new MutationObserver(annotateCodeBlocks);
observer.observe(targetNode, config);
