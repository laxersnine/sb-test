import asyncio
import os
import subprocess
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from jira import JIRA

class Inputs:
    def __init__(
            self,
            GITHUB_TOKEN,
            REPO_MERGED_BRANCH,
            GITHUB_API_URL,
            REPO_NAME,
            REPO_OWNER,
            TRIGGERED_BY,
            JIRA_URL,
            JIRA_ACCOUNT,
            JIRA_TOKEN
            ):
        self.GITHUB_API_URL = GITHUB_API_URL 
        self.GITHUB_TOKEN = GITHUB_TOKEN
        self.JIRA_ACCOUNT = JIRA_ACCOUNT
        self.JIRA_TOKEN = JIRA_TOKEN
        self.JIRA_URL = JIRA_URL
        self.REPO_MERGED_BRANCH = REPO_MERGED_BRANCH 
        self.REPO_NAME = REPO_NAME
        self.REPO_OWNER = REPO_OWNER
        self.TRIGGERED_BY = TRIGGERED_BY


def get_inputs():
    try:
        GITHUB_API_URL = "https://api.github.com/graphql"
        GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
        REPO_MERGED_BRANCH = os.environ["REPO_MERGED_BRANCH"]
        REPO_NAME = os.environ["REPO_NAME"]
        REPO_OWNER = os.environ["REPO_OWNER"]
        TRIGGERED_BY = os.environ["TRIGGERED_BY"]
        JIRA_URL = os.environ["JIRA_URL"]
        JIRA_ACCOUNT = os.environ["JIRA_ACCOUNT"]
        JIRA_TOKEN = os.environ["JIRA_TOKEN"]
        return Inputs(
            GITHUB_TOKEN,
            REPO_MERGED_BRANCH,
            GITHUB_API_URL,
            REPO_NAME,
            REPO_OWNER,
            TRIGGERED_BY,
            JIRA_URL,
            JIRA_ACCOUNT,
            JIRA_TOKEN
            )
    except KeyError as e:
        print(e)
        raise

def init_gql_client(url, auth_token):
    transport = AIOHTTPTransport(url = url, headers = {"Authorization": "Bearer " + auth_token })
    client = Client(transport=transport, fetch_schema_from_transport=True)

    return client

def is_target_larger_then_base(target_version, base_version):
    target_version_parts = target_version.split(".")
    base_version_parts = base_version.split(".")

    for i in range(0, len(target_version_parts)):
        if (len(base_version_parts) <= i):
            return True
        elif (int(target_version_parts[i]) > int(base_version_parts[i])):
            return True
        elif (int(target_version_parts[i]) < int(base_version_parts[i])):
            return False
    return False

async def get_target_branches(client, params, base_version):
    release_version_query = gql(
        """
        query getReleaseVersions($repo:String!, $owner:String!) {
            repository(owner: $owner, name: $repo){
                id,
                refs(first: 100, refPrefix: "refs/heads/release/") {
                    nodes {
                        name
                        prefix
                    }
                }
            }
        }
    """
    )

    result = await client.execute(release_version_query, variable_values = params)

    params["repositoryId"] = result["repository"]["id"]

    release_versions = result["repository"]["refs"]["nodes"]

    target_branches = []

    for v in release_versions:
        version = v["name"]
        if (is_target_larger_then_base(version, base_version)):
            target_branches.append(v["prefix"] + v["name"])
    return target_branches

async def create_pull_request(client, params, base_branch):
    p = params.copy()
    p["baseBranch"] = base_branch
    p["title"] = "(Automated) " + params['headBranch'] + " into " + base_branch
    p['body'] = "Triggered by " + params['triggeredBy']

    print("Creating pull request for " + params['headBranch'] + " into " + base_branch + "...")

    pull_request_query = gql(
        """
        mutation createPullRequest($repositoryId:ID!, $baseBranch:String!, $headBranch:String!, $title:String!, $body:String!) {
            createPullRequest(input: {repositoryId: $repositoryId, baseRefName: $baseBranch, headRefName: $headBranch, title: $title , body: $body}) {
                pullRequest {
                    id
                    number
                    mergeable
                    title
                    url
                    baseRef {
                        name
                    }
                    headRef {
                        name
                    }
                }
            }
        }
    """
    )
    try:
        pull_request = (await client.execute(pull_request_query, variable_values = p))["createPullRequest"]["pullRequest"]
        print("Created pull request " + str(pull_request["number"]) + " for " + base_branch)
    except TransportQueryError as e:
            print(e)
            pull_request = None
    return pull_request

async def create_pull_requests(client, params, base_branches):
    #loop = asyncio.get_running_loop()
    results = await asyncio.gather(*[create_pull_request(client, params, base_branch) for base_branch in base_branches])
    #results = loop.run_until_complete(looper)
    return filter(lambda r: r != None, results)
    
async def get_pull_request(client, params, pr_number):
    p = params.copy()
    p["number"] = pr_number
    pull_request_query = gql(
        """
        query pullRequest($repo:String!, $owner:String!, $number:Int!) {
            repository(name:$repo, owner:$owner) { 
                pullRequest(number: $number) {
                    id
                    number
                    mergeable
                    title
                    url
                    baseRef {
                        name
                    }
                    headRef {
                        name
                    }
                }
            }
        }
    """
    )

    # Execute the query on the transport
    pullRequest = (await client.execute(pull_request_query, variable_values = p))["repository"]["pullRequest"]

    return pullRequest

async def is_pr_mergeable(client, params, pull_request):
    match pull_request["mergeable"]:
        case "CONFLICTING":
            print("Pull request " + str(pull_request["number"]) + " is conflicting")
            return False
        case "UNKNOWN":
            print("Pull request " + str(pull_request["number"]) + " is unknown")
            await asyncio.sleep(60)
            pull_request = await get_pull_request(client, params, pull_request["number"])
            return await is_pr_mergeable(client, params, pull_request)
        case "MERGEABLE":
            print("Pull request " + str(pull_request["number"]) + " is mergeable")
            return True
        
async def approve_pull_request(client, params, pull_request):
    p = params.copy()
    p["pullRequestId"] = pull_request["id"]
    approve_pull_request_query = gql(
        """
        mutation approvePullRequest($pullRequestId:ID!) {
            addPullRequestReview(input: {event: APPROVE, pullRequestId: $pullRequestId}) {
                pullRequestReview {
                    id
                    state
                }
            }
        }
    """
    )

    await client.execute(approve_pull_request_query, variable_values = p)

async def merge_pull_request(client, params, pull_request):
    #gh pr merge pull_request["url"] --merge --admin -d
    subprocess.run(["gh", "pr", "merge", pull_request["url"], "--merge", "--admin", "-d"])

    # await approve_pull_request(client, params, pull_request)
    # p = params.copy()
    # p["pullRequestId"] = pull_request["id"]
    # merge_pull_request_query = gql(
    #     """
    #     mutation mergePullRequest($pullRequestId:ID!) {
    #         mergePullRequest(input: {pullRequestId: $pullRequestId, mergeMethod: MERGE}) {
    #             pullRequest {
    #                 id
    #                 number
    #                 mergeable
    #                 title
    #                 url
    #                 baseRef {
    #                     name
    #                 }
    #                 headRef {
    #                     name
    #                 }
    #             }
    #         }
    #     }
    # """
    # )

    # await client.execute(merge_pull_request_query, variable_values = p)

def create_jira(pull_request):
    inputs = get_inputs()
    jira = JIRA(inputs.JIRA_URL, basic_auth=(inputs.JIRA_ACCOUNT, inputs.JIRA_TOKEN))
    issue_data = {
        "project": {"key": "SB"},
        "summary": "(Automation) Resolve conflicts - " + pull_request["headRef"]["name"].replace("release/", "") + " into " + pull_request["baseRef"]["name"].replace("release/", "") + "#" + str(pull_request["number"]),
        "description": pull_request["url"],
        "issuetype": {"name": "Task"},
        "fixVersions": [{"name": "R" + pull_request["baseRef"]["name"].replace("release/", "")}],
        "labels": ["automation", "merge_conflicts"]
    }
    issue = jira.create_issue(fields=issue_data)
    print("Created Jira issue: " + issue.key)


async def process_pull_request(client, params, pull_request):
    print("Processing pull request " + str(pull_request["number"]))
    if await is_pr_mergeable(client, params, pull_request):
        print("Pull request " + str(pull_request["number"]) + " is mergeable")
        await merge_pull_request(client, params, pull_request)
    else:
        print("Pull request " + str(pull_request["number"]) + " is not mergeable, start to create on Jira...")
        create_jira(pull_request)

async def process_pull_requests(client, params, pull_requests):
    #loop = asyncio.get_event_loop()
    await asyncio.gather(*[process_pull_request(client, params, pull_request) for pull_request in pull_requests])
    #results = loop.run_until_complete(looper)

async def main():
    inputs = get_inputs()
    print("Auto sync starts, getting merged event for branch " + inputs.REPO_MERGED_BRANCH + " triggered by " + inputs.TRIGGERED_BY)

    if (not inputs.REPO_MERGED_BRANCH.startswith("refs/heads/release")):
        print("Not a release branch")
        exit(0)

    head_version = inputs.REPO_MERGED_BRANCH.replace("refs/heads/release/", "")
    
    async with init_gql_client(inputs.GITHUB_API_URL, inputs.GITHUB_TOKEN) as client:
        params = {"repo": inputs.REPO_NAME, "owner": inputs.REPO_OWNER, "headBranch": inputs.REPO_MERGED_BRANCH, "triggeredBy": inputs.TRIGGERED_BY}

        print("Get release branch list...")

        base_branches = await get_target_branches(client, params, head_version)
        print("Found " + str(len(base_branches)) + " branches to sync")

        pull_requests = await create_pull_requests(client, params, base_branches)

        await process_pull_requests(client, params, pull_requests)

    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
