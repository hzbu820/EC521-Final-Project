async function getGitLabProjectInfo(projectIdentifier) {
  // projectIdentifier can be:
  // 1. The numerical ID of the project (e.g., '278964')
  // 2. The full path with namespace, URL-encoded (e.g., 'gitlab-org%2Fgitlab-runner')
  const encodedIdentifier = encodeURIComponent(projectIdentifier);
  const url = `https://gitlab.com/api/v4/projects/${encodedIdentifier}`;

  try {
    const response = await fetch(url, {
      headers: {
        // Optional: For higher rate limits or private projects, add an Authorization header:
        // 'Authorization': 'Bearer YOUR_GITLAB_PERSONAL_ACCESS_TOKEN'
        // Make sure your token has the 'read_api' scope.
      },
    });

    // Check if the response was successful (status code 200-299)
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(
          `Project "${projectIdentifier}" not found on GitLab. (Or invalid token/permissions for private project)`,
        );
      } else if (response.status === 401) {
        throw new Error(
          `Unauthorized: Check your GitLab Personal Access Token or project visibility.`,
        );
      } else if (response.status === 403) {
        // This could indicate rate limit or Forbidden access
        throw new Error(
          `Forbidden access or GitLab API rate limit exceeded. Try again later or use a Personal Access Token.`,
        );
      }
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data; // This will contain all the project information
  } catch (error) {
    console.error("Error fetching GitLab project information:", error.message);
    return null; // Or re-throw the error, depending on your error handling strategy
  }
}

// --- How to use it ---

// Example 1: Get information about a popular public project using its path with namespace
// (e.g., GitLab Runner project from gitlab-org)
getGitLabProjectInfo("gitlab-org/gitlab-runner")
  .then((info) => {
    if (info) {
      console.log("--- Project: gitlab-org/gitlab-runner ---");
      console.log("ID:", info.id);
      console.log("Name:", info.name);
      console.log("Full Path:", info.path_with_namespace);
      console.log("Description:", info.description);
      console.log("Stars:", info.star_count); // This is the number of stars!
      console.log("Forks:", info.forks_count);
      console.log("Default Branch:", info.default_branch);
      console.log("Web URL:", info.web_url);
      console.log("Visibility:", info.visibility);
      // console.log("Full Info:", info); // Uncomment to see all available data
    }
  })
  .catch((error) => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 2: Get information about another public project (e.g., markdown-it from markdown-it organization)
// // using its path with namespace
// getGitLabProjectInfo('markdown-it/markdown-it')
//   .then(info => {
//     if (info) {
//       console.log("--- Project: markdown-it/markdown-it ---");
//       console.log("Name:", info.name);
//       console.log("Stars:", info.star_count);
//       console.log("Web URL:", info.web_url);
//     }
//   })
//   .catch(error => console.error("Caught error:", error));

// console.log("\n---"); // Separator for clarity

// // Example 3: Handle a non-existent project
// getGitLabProjectInfo('non-existent-group/non-existent-project-12345')
//   .then(info => {
//     if (info) {
//       console.log("This should not be reached for a non-existent project.");
//     }
//   })
//   .catch(error => console.error("Caught error for non-existent project:", error.message));
