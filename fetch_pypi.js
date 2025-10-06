/**
 * @file fetch_pypi.js
 * @date 2025-10-06
 * @author Victor Mercola (vmercola)
 */

/**
 * Get the JSON metadata of a package from its name on the Python Package Index (PyPI).
 *
 * @param packageName package name
 * @returns JSON file from PyPI.
 */
async function getPyPIPackageInfo(packageName) {
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
    return data; // This will contain all the package information
  } catch (error) {
    console.error("Error fetching package information:", error.message);
    return null; // Or re-throw the error, depending on your error handling strategy
  }
}

// --- How to use it ---

// Example 1: Get information about a well-known package (e.g., 'requests')
getPyPIPackageInfo("requests")
  .then((pkg_info) => {
    if (pkg_info) {
      console.log("--- Package: requests ---");
      console.log("Latest Version:", pkg_info.info.version);
      console.log("Summary:", pkg_info.info.summary);
      console.log("Project URL:", pkg_info.info.project_url);
      console.log("License:", pkg_info.info.license);
      console.log("Author:", pkg_info.info.author);
      console.log("Source:", pkg_info.info.project_urls.Source);
      // console.log("Full Info:", info); // Uncomment to see all available data
    }
  })
  .catch((error) => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 2: Get information about another package (e.g., 'numpy')
// getPyPIPackageInfo("numpy")
//   .then((info) => {
//     if (info) {
//       console.log("--- Package: numpy ---");
//       console.log("Latest Version:", info.info.version);
//       console.log("Summary:", info.info.summary);
//     }
//   })
//   .catch((error) => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 3: Handle a non-existent package
// getPyPIPackageInfo("non-existent-package-12345")
//   .then((info) => {
//     if (info) {
//       console.log("This should not be reached for a non-existent package.");
//     }
//   })
//   .catch((error) =>
//     console.error("Caught error for non-existent package:", error.message),
//   );
