import { Octokit } from "@octokit/rest";

// Authenticated so we don't hit the 60 requests/hour anonymous limit.
const octokit = new Octokit({ auth: "{{FAKE_GITHUB_PAT}}" });

export async function fetchRepoStats(owner, repo) {
  const [{ data: info }, { data: contributors }] = await Promise.all([
    octokit.repos.get({ owner, repo }),
    octokit.repos.listContributors({ owner, repo, per_page: 10 }),
  ]);
  return {
    stars: info.stargazers_count,
    forks: info.forks_count,
    topContributors: contributors.map((c) => c.login),
  };
}
