const authorization = null;

async function getGitHubRepoInfo(owner, repo) {
  const url = `https://api.github.com/repos/${owner}/${repo}`;

  try {
    const response = await fetch(url, {
      headers: {
        // Optional: GitHub API best practice to include a User-Agent header
        "User-Agent": "EC521-Final-Project-JS",
        // For higher rate limits, you can add an Authorization header with a Personal Access Token:
        // 'Authorization': 'token YOUR_GITHUB_PERSONAL_ACCESS_TOKEN'
      },
    });

    // Check if the response was successful (status code 200-299)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Repository "${owner}/${repo}" not found on GitHub.`);
      } else if (response.status === 403) {
        // This often indicates a rate limit issue if no token is used,
        // or permission issue if a token is used but invalid/insufficient.
        const rateLimitReset = response.headers.get("X-RateLimit-Reset");
        const resetTime = rateLimitReset
          ? new Date(rateLimitReset * 1000).toLocaleTimeString()
          : "unknown";
        throw new Error(
          `GitHub API rate limit exceeded or forbidden access. Try again after ${resetTime} or use a Personal Access Token.`,
        );
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data; // This will contain all the repository information
  } catch (error) {
    console.error(
      "Error fetching GitHub repository information:",
      error.message,
    );
    return null; // Or re-throw the error, depending on your error handling strategy
  }
}

// --- How to use it ---

// Example 1: Get information about a popular repository (e.g., 'facebook/react')
getGitHubRepoInfo("facebook", "react")
  .then((info) => {
    if (info) {
      console.log("--- Repository: facebook/react ---");
      console.log("Name:", info.name);
      console.log("Description:", info.description);
      console.log("Stars:", info.stargazers_count); // This is the number of stars!
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

// // Example 2: Get information about another repository (e.g., 'twbs/bootstrap')
// getGitHubRepoInfo('twbs', 'bootstrap')
//   .then(info => {
//     if (info) {
//       console.log("--- Repository: twbs/bootstrap ---");
//       console.log("Name:", info.name);
//       console.log("Stars:", info.stargazers_count);
//       console.log("Language:", info.language);
//     }
//   })
//   .catch(error => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 3: Handle a non-existent repository
// getGitHubRepoInfo('non-existent-user-12345', 'non-existent-repo-67890')
//   .then(info => {
//     if (info) {
//       console.log("This should not be reached for a non-existent repository.");
//     }
//   })
//   .catch(error => console.error("Caught error for non-existent repo:", error.message));

// console.log("\n---"); // Separator for clarity

// Example 4: GitHub API rate limit demonstration (you might hit this if you make too many requests quickly without authentication)
// Uncomment and run multiple times in a short period to test rate limiting.
// getGitHubRepoInfo('octocat', 'Spoon-Knife')
//   .then(info => {
//     if (info) {
//       console.log("--- Repository: octocat/Spoon-Knife ---");
//       console.log("Stars:", info.stargazers_count);
//     }
//   })
//   .catch(error => console.error("Caught error for Spoon-Knife:", error.message));
