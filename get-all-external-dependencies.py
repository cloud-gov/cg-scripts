#!ENV/bin/python

import glob
import yaml
import urllib.request
import urllib.error
import json
from base64 import b64encode
from multiprocessing import Pool
import sys


# need a personal access token to avoid anon rate limits, it doesn't need any
# scopes
# https://github.com/settings/tokens
AUTH = b64encode(b"github_username:token").decode('ascii')


def boshio_release_to_source(resource):
    """Look up the github source for a given bosh release

    Args:
        resource (dict): A bosh-io-release resource from a concourse pipeline
    """
    bosh_api_url = "https://bosh.io/api/v1/releases/github.com/{0}"
    bosh_api_url = bosh_api_url.format(resource['source']['repository'])

    req = urllib.request.Request(bosh_api_url, headers={"User-Agent": "curl"})
    with urllib.request.urlopen(req) as api:
        uri = "https://" + json.loads(api.read().decode('utf-8'))[0]['name']
        return (uri, 'master')


def get_commit(owner, repo, path):
    """Use the GitHub api to retrieve the submodule info for a given path

    Args:
        owner (str): The owner of the repo
        repo (str): The name of the repo
        path (str): The path to the submodule in the repo.

    Returns:
        tuple(str, str): The url to the submodule repo, and the sha of the
        commmit
    """
    github_api_url = "https://api.github.com/repos/{0}/{1}/contents/{2}"
    github_api_url = github_api_url.format(owner, repo, path)
    req = urllib.request.Request(github_api_url,
                                 headers={"Authorization": "Basic "+AUTH})
    with urllib.request.urlopen(req) as api:
        info = json.loads(api.read().decode('utf-8'))
        return (info['submodule_git_url'], info['sha'])


def find_submodules(source):
    """Use the GitHub api to return a list of submodules for a given source

    Args:
        source(tuple(repo, branch)) - The repo and branch to find submodules
        for

    Return
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
                                     headers={"Authorization": "Basic "+AUTH})
        with urllib.request.urlopen(req) as api:
            tree = json.loads(api.read().decode('utf-8'))

            if tree['truncated']:
                raise SystemExit("Unable to scan {0} for submodules. "
                                 "Tree is too large".format(source[0]))

            for item in tree['tree']:
                if item['type'] == 'commit':
                    sub = get_commit(owner, repo, item['path'])
                    submodules.append(sub)
                    submodules += find_submodules((sub[0], sub[1]))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            pass
        else:
            print(exc)
            print(exc.read())
            raise exc

    return submodules


def get_lang(source):
    """Use the github API to find out which languages a paricular source use

    Args:
        source(tuple(repo, branch)) - The repo and branch to find the
        languages in use.

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
                                 headers={"Authorization": "Basic "+AUTH})
    with urllib.request.urlopen(req) as api:
        info = json.loads(api.read().decode('utf-8'))
        source.append(sorted(info, key=info.get, reverse=True))

        return source


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


def basename(source):
    """Given http://github.com/foo/bar-baz.git return foo-bar-baz"""

    repo_url = source[0].rstrip('/')
    owner = repo_url.split('/')[-2]
    repo = repo_url.split('/')[-1]

    if repo.endswith('.git'):
        repo = repo[:-4]

    return "{0}-{1}-{2}".format(owner, repo, source[1])

if __name__ == "__main__":
    # STEP 0: Download all concourse pipelines
    # for p in `fly -t fr pipelines | awk '{print $1}'`; \
    # do fly -t fr gp -p ${p} > ${p}.yml; done

    # STEP 1: parse pipelines for sources
    sources = []
    for pipeline in glob.glob(sys.argv[1]+'/*.yml'):
        with open(pipeline) as fh:
            parsed = yaml.load(fh)

            with Pool(processes=10) as p:
                for s in p.map(resource_to_sources, parsed['resources']):
                    if s is None:
                        continue

                    sources.append(tuple(s))

    sources = list(set(sources))

    # STEP 2: parse sources for submodule
    # Many CF "repos" are actually just collections of other repos as
    # submodules pinned to specific commits as a "release"
    submodules = []
    with Pool(processes=10) as p:
        for s in p.map(find_submodules, sources):
            submodules += s

    all_repos = list(set([tuple(x) for x in sources] +
                         [tuple(x) for x in submodules]))

    # STEP 3: Ask GitHub which languages are used in a given repo
    with Pool(processes=10) as p:
        final = p.map(get_lang, all_repos)

    print(json.dumps(final))

    for source in final:
        print("{0}\t{1}\t{2}".format(source[0], source[1],
                                     ", ".join(source[2])))
