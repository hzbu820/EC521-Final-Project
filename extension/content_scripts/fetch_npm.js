async function getNpmPackageInfo(packageName) {
  // The NPM Registry API endpoint for a package
  const url = `https://registry.npmjs.org/${packageName}`;

  try {
    const response = await fetch(url);

    // Check if the response was successful (status code 200-299)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`NPM package "${packageName}" not found.`);
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data; // This will contain all the package information
  } catch (error) {
    console.error("Error fetching NPM package information:", error.message);
    return null; // Or re-throw the error, depending on your error handling strategy
  }
}

// --- How to use it ---

// Example 1: Get information about a popular package (e.g., 'react')
getNpmPackageInfo("react")
  .then((info) => {
    if (info) {
      console.log("--- NPM Package: react ---");
      console.log("Name:", info.name);
      console.log("Latest Version:", info["dist-tags"].latest); // Get the latest version from dist-tags
      console.log("Description:", info.description);
      console.log("License:", info.license);
      console.log("Author:", info.author ? info.author.name : "N/A");
      console.log("Homepage:", info.homepage);

      // You can also access specific versions and their details
      const latestVersionData = info.versions[info["dist-tags"].latest];
      if (latestVersionData) {
        console.log(
          "Dependencies (latest version):",
          Object.keys(latestVersionData.dependencies || {}).join(", "),
        );
        console.log(
          "Repository URL:",
          latestVersionData.repository
            ? latestVersionData.repository.url
            : "N/A",
        );
      }
      // console.log("Full Info:", info); // Uncomment to see all available data
    }
  })
  .catch((error) => console.error("Caught error:", error));

console.log("\n---"); // Separator for clarity

// // Example 2: Get information about another package (e.g., 'express')
// getNpmPackageInfo("express")
//   .then((info) => {
//     if (info) {
//       console.log("--- NPM Package: express ---");
//       console.log("Name:", info.name);
//       console.log("Latest Version:", info["dist-tags"].latest);
//       console.log("Description:", info.description);
//       console.log(
//         "Maintainers:",
//         info.maintainers.map((m) => m.name).join(", "),
//       );
//     }
//   })
//   .catch((error) => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 3: Handle a non-existent package
// getNpmPackageInfo("non-existent-npm-package-12345")
//   .then((info) => {
//     if (info) {
//       console.log("This should not be reached for a non-existent package.");
//     }
//   })
//   .catch((error) =>
//     console.error("Caught error for non-existent package:", error.message),
//   );
