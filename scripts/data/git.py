import os

"""
From: https://<git repo>/<path el 1>/<path el 2>/<path el 3>/<path el 4>
To: git@<git repo>:<path el 1>/<path el 2>/<path el 3>/<path el 4>.git
"""
def url_HTTPS_to_SSH(url):
    if not url.startswith("https"):
        if not url.startswith("git@"):
            raise Exception("Cannot convert " + url)
        else:
            # Already in ssh format
            return url

    if url.endswith(".git"):
        url = url[:-4]

    # split and remove repeated  '/'
    split_url = [ x for x in url.split("/") if len(x) != 0]
    return "git@" + split_url[1] + ":" + '/'.join(split_url[2:])+".git"

"""
From: git@<git repo>:<path el 1>/<path el 2>/<path el 3>/<path el 4>.git
To: https://<git repo>/<path el 1>/<path el 2>/<path el 3>/<path el 4>
"""
def url_SSH_to_HTTPS(url):
    if not url.startswith("git@"):
        if not url.startswith("https"):
            raise Exception("Cannot convert " + url)
        else:
            # Already in ssh format
            return url

    head, path = url.split(":")
    remote = head.split("@")[1]

    if path.endswith(".git"):
        path = path[:-4]

    return "https://" + remote + "/" + path

"""
Flip url. If ssh url, change to HTTP and vice-versa
"""
def FlipUrl(url):
    if url.startswith("git@"):
        return url_SSH_to_HTTPS(url)
    elif url.startswith("https"):
        return url_HTTPS_to_SSH(url)
    else:
        raise Exception("Cannot convert " + url)


def GetRepoNameFromURL(Url):
    if Url == None or len(Url) == 0:
        raise Exception("Requested URL ("+Url+") is empty")
    Url = url_SSH_to_HTTPS(Url)

    if Url[-1] == '/':
        Url = Url[:-1]

    Url = Url.split('/')[-1].strip()
    if Url.endswith(".git"):
        Url = Url[:-4]
    return Url

def GetRepoBareTreePath(url):
    url = url_SSH_to_HTTPS(url)
    if url[-1] == '/':
        url = url[:-1]
    url = url.replace("https://","")
    url = url.replace("http://","")
    if not url.endswith(".git"):
        url = url+".git"
    return url

def SameUrl(url1, url2):
    return url_SSH_to_HTTPS(url1) == url_SSH_to_HTTPS(url2)
