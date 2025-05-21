#!/usr/bin/env python3

import argparse
import functools
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
import yaml

from base64 import b64encode
from multiprocessing import Pool


def boshio_release_to_source(resource):
    """Look up the github source for a given bosh release

    Args:
        resource (dict): A bosh-io-release resource from a concourse pipeline

    Returns:
        tuple(str, str): The url to the repo, and the branch

    """
    bosh_api_url = "https://bosh.io/api/v1/releases/github.com/{0}"
    bosh_api_url = bosh_api_url.format(resource['source']['repository'])

    req = urllib.request.Request(bosh_api_url, headers={"User-Agent": "curl"})
    with urllib.request.urlopen(req) as api:
        uri = "https://" + json.loads(api.read().decode('utf-8'))[0]['name']
        return (uri, 'master')


def get_commit(owner, repo, path, auth):
    """Use the GitHub api to retrieve the submodule info for a given path

    Args:
        owner (str): The owner of the repo
        repo (str): The name of the repo
        path (str): The path to the submodule in the repo.

    Returns:
        tuple(str, str): The url to the submodule repo, and the sha of the
        commit
    """
    github_api_url = "https://api.github.com/repos/{0}/{1}/contents/{2}"
    github_api_url = github_api_url.format(owner, repo, path)
    req = urllib.request.Request(github_api_url,
                                 headers={"Authorization": "Basic "+auth})
    with urllib.request.urlopen(req) as api:
        info = json.loads(api.read().decode('utf-8'))
        return (info['submodule_git_url'], info['sha'])


def find_submodules(source, auth):
    """Use the GitHub api to return a list of submodules for a given source

    Args:
        source(tuple(repo, branch)) - The repo and branch to find submodules
        for

    Returns:
        List of tuples: [(repo, branch)] - A list of submodules.

    """
    repo_url, branch = source

    owner = repo_url.split('/')[-2]
    repo = repo_url.split('/')[-1]

    if repo.endswith('.git'):
        repo = repo[:-4]

    submodules = []

    github_api_url = "https://api.github.com/repos/{0}/{1}/git/trees/{2}?" \
                     "recursive=true"
    github_api_url = github_api_url.format(owner, repo, branch)
    try:
        req = urllib.request.Request(github_api_url,
                                     headers={"Authorization": "Basic "+auth})
        with urllib.request.urlopen(req) as api:
            tree = json.loads(api.read().decode('utf-8'))

            if tree['truncated']:
                raise SystemExit("Unable to scan {0} for submodules. "
                                 "Tree is too large".format(source[0]))

            for item in tree['tree']:
                if item['type'] == 'commit':
                    sub = get_commit(owner, repo, item['path'], auth)
                    submodules.append(sub)
                    submodules += find_submodules((sub[0], sub[1]), auth)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            pass
        else:
            print(exc)
            print(exc.read())
            raise exc

    return submodules


def get_lang(source, auth):
    """Use the github API to find out which languages a particular source use

    Args:
        source(tuple(repo, branch)) - The repo and branch to find the
        languages in use.

    Returns:
        tuple(repo, branch, langs) - The source object with langs appended to it

    """
    source = list(source)

    if 'github' not in source[0]:
        if source[0].split('/')[2] in ['gopkg.in', 'go.googlesource.com']:
            source.append(['Go'])
            return source

    repo_url = source[0].rstrip('/')
    owner = repo_url.split('/')[-2]
    repo = repo_url.split('/')[-1]

    if repo.endswith('.git'):
        repo = repo[:-4]

    github_api_url = "https://api.github.com/repos/{0}/{1}/languages"
    github_api_url = github_api_url.format(owner, repo)

    req = urllib.request.Request(github_api_url,
                                 headers={"Authorization": "Basic "+auth})
    try:
        with urllib.request.urlopen(req) as api:
            info = json.loads(api.read().decode('utf-8'))
            source.append(sorted(info, key=info.get, reverse=True))

            return source
    except Exception as exc:
        print(exc)
        print(exc.read())
        raise exc


def resource_to_sources(resource):
    """Given a concourse resource, expand it to a git url, and branch

    Args:
        resource (dict): A bosh-io-release resource from a concourse pipeline
    """

    if resource['type'] == 'git':
        return (resource['source']['uri'], resource['source']['branch'])

    if resource['type'] == 'bosh-io-release':
        return boshio_release_to_source(resource)

    return None


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate a report of all repos referenced by a Concourse instance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('concourse_url', help="The URL to a concourse instance")
    parser.add_argument('github_username', help="The github username to authenticate as")
    parser.add_argument('github_token', help="The github token for the github user (no scopes are required, this is simply to avoid anon rate limits).  Get a token at: https://github.com/settings/tokens")
    parser.add_argument('--internal-org', default="18F", help="If a repo is owned by this github org, it is considered `Internal`")
    parser.add_argument('--json', default=False, action='store_true', help="Output JSON instead of tab delimited")

    args = parser.parse_args()

    # generate the auth header we'll use for http requests to github
    AUTH = b64encode("{github_username}:{github_token}".format(**vars(args)).encode('ascii')).decode('ascii')

    # make sure we can execute fly, and find the given target
    FLY_TARGET = None
    try:
        for target in subprocess.check_output(['fly', 'targets']).decode('utf-8').split("\n"):
            target = target.strip()
            if not target:
                continue

            name, uri, _ = re.split("\s+", target, 2)

            if uri == args.concourse_url:
                FLY_TARGET = name
                break
    except subprocess.CalledProcessError as exc:
        parser.error("Unable to execute fly: {0}".format(exc))

    if FLY_TARGET is None:
        parser.error("Could not find fly target for {0}; ensure it appears in `fly targets`".format(args.concourse_url))

    # STEP 1: extract all sources from all pipelines in concourse
    sources = []
    try:
        for pipeline in subprocess.check_output(['fly', '-t', FLY_TARGET, 'pipelines']).decode('utf-8').split("\n"):
            pipeline = pipeline.strip()
            if not pipeline:
                continue
            pipeline, _ = pipeline.split(" ", 1)

            print("Scanning {0}".format(pipeline), file=sys.stderr)
            parsed = yaml.load(
                subprocess.check_output(['fly', '-t', FLY_TARGET, 'gp', '-p', pipeline]).decode('utf-8')
            )

            # expand all concourse resources that link to repos to the underlying repo
            with Pool(processes=10) as p:
                for s in p.map(resource_to_sources, parsed['resources']):
                    if s is None:
                        continue

                    sources.append(tuple(s))

        # dedupe the list
        sources = list(set(sources))
    except subprocess.CalledProcessError as exc:
        parser.error("Unable to execute fly: {0}".format(exc))

    # STEP 2: parse sources for submodule
    # Many CF "repos" are actually just collections of other repos as
    # submodules pinned to specific commits as a "release"
    submodules = []
    print("Finding submodules (this may take a while)".format(pipeline), file=sys.stderr)
    with Pool(processes=10) as p:
        for s in p.map(functools.partial(find_submodules, auth=AUTH), sources):
            submodules += s

    # dedupe the list
    all_repos = list(set([tuple(x) for x in sources] +
                         [tuple(x) for x in submodules]))

    # STEP 3: Ask GitHub which languages are used in a given repo
    print("Identifying languages".format(pipeline), file=sys.stderr)
    with Pool(processes=10) as p:
        final = p.map(functools.partial(get_lang, auth=AUTH), all_repos)

    # STEP 4: Identify which ones we own
    for source in final:
        if source[0].lower().split('/')[-2] == args.internal_org.lower():
            owner = "Internal"
        else:
            owner = "External"
        source.append(owner)

    # Output in the format requested
    if args.json:
        print(json.dumps(final))
    else:
        print("\t".join(['Repo', 'Branch', 'Lang(s)', 'Internal/External']))
        for source in final:
            source[2] = ",".join(source[2])
            print("\t".join(source))

    raise SystemExit(0)
