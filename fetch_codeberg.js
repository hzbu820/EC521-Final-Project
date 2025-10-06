async function getCodebergRepoInfo(owner, repo) {
  const url = `https://codeberg.org/api/v1/repos/${owner}/${repo}`;

  try {
    const response = await fetch(url, {
      headers: {
        // Optional: Including a User-Agent header is good practice for APIs
        "User-Agent": "Codeberg-Info-Fetcher-JS",
        // For higher rate limits or private projects, you can add an Authorization header:
        // 'Authorization': 'token YOUR_CODEBERG_PERSONAL_ACCESS_TOKEN'
        // Create a token under User Settings -> Applications -> Manage Access Tokens.
      },
    });

    // Check if the response was successful (status code 200-299)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Repository "${owner}/${repo}" not found on Codeberg.`);
      } else if (response.status === 403 || response.status === 401) {
        // 403 Forbidden or 401 Unauthorized could indicate rate limit or token issues
        throw new Error(
          `Codeberg API rate limit exceeded, forbidden access, or invalid token. Check permissions/token.`,
        );
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data; // This will contain all the repository information
  } catch (error) {
    console.error(
      "Error fetching Codeberg repository information:",
      error.message,
    );
    return null; // Or re-throw the error, depending on your error handling strategy
  }
}

// --- How to use it ---

// Example 1: Get information about a popular Codeberg repository (e.g., 'forgejo/forgejo')
getCodebergRepoInfo("forgejo", "forgejo")
  .then((info) => {
    if (info) {
      console.log("--- Repository: forgejo/forgejo ---");
      console.log("ID:", info.id);
      console.log("Name:", info.name);
      console.log("Description:", info.description);
      console.log("Stars:", info.stars_count); // This is the number of stars!
      console.log("Forks:", info.forks_count);
      console.log("Language:", info.language);
      console.log("Open Issues:", info.open_issues_count);
      console.log(
        "Last Updated:",
        new Date(info.updated_at).toLocaleDateString(),
      );
      console.log("URL:", info.html_url);
      // console.log("Full Info:", info); // Uncomment to see all available data
    }
  })
  .catch((error) => console.error("Caught error:", error));

console.log("\n---"); // Separator for clarity

// // Example 2: Get information about another Codeberg repository (e.g., 'codeberg/docs')
// getCodebergRepoInfo("codeberg", "docs")
//   .then((info) => {
//     if (info) {
//       console.log("--- Repository: codeberg/docs ---");
//       console.log("Name:", info.name);
//       console.log("Stars:", info.stars_count);
//       console.log("Language:", info.language);
//       console.log("Open Issues:", info.open_issues_count);
//     }
//   })
//   .catch((error) => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 3: Handle a non-existent repository
// getCodebergRepoInfo("non-existent-user-12345", "non-existent-repo-67890")
//   .then((info) => {
//     if (info) {
//       console.log("This should not be reached for a non-existent repository.");
//     }
//   })
//   .catch((error) =>
//     console.error("Caught error for non-existent repo:", error.message),
//   );
