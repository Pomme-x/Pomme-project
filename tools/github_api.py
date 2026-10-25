# -*- coding: utf-8 -*-
"""用 GitHub REST API 直接上传文件（不需要本机安装 git）。

一次上传 = 一个 commit（Git Data API），提交后 GitHub Actions 自动部署。
"""

import base64
import json
import time
import urllib.error
import urllib.request

API = 'https://api.github.com'
UA = 'PommeTool/1.0'


class GitHubAPI:
    def __init__(self, token, repo, branch='main'):
        self.token = token
        self.repo = repo
        self.branch = branch

    # -------- 基础请求 --------
    def _request(self, method, url, payload=None):
        data = None
        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.github+json',
            'User-Agent': UA,
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                return json.loads(body.decode('utf-8')) if body else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')
            try:
                msg = json.loads(msg).get('message', msg)
            except Exception:
                pass
            raise RuntimeError('GitHub API %s %s 失败：%s' % (method, url.split('/repos/')[-1], msg))
        except urllib.error.URLError as e:
            raise RuntimeError('连不上 GitHub：%s' % e.reason)

    def _repo_url(self, suffix=''):
        return '%s/repos/%s%s' % (API, self.repo, suffix)

    # -------- 读取 --------
    def get_file(self, path):
        """返回 (bytes, sha)；文件不存在返回 (None, None)。"""
        try:
            data = self._request('GET', self._repo_url('/contents/%s?ref=%s' % (path, self.branch)))
        except RuntimeError as e:
            if '404' in str(e) or 'Not Found' in str(e):
                return None, None
            raise
        if data.get('content'):
            return base64.b64decode(data['content']), data['sha']
        return None, data.get('sha')

    def get_text(self, path):
        data, sha = self.get_file(path)
        if data is None:
            return None, None
        return data.decode('utf-8'), sha

    def latest_commit_sha(self):
        ref = self._request('GET', self._repo_url('/git/ref/heads/' + self.branch))
        return ref['object']['sha']

    # -------- 一次提交多个文件 --------
    def commit_files(self, files, message, deletions=None):
        """files: {path: bytes}；deletions: 需要删除的 path 列表。返回 commit sha。"""
        base_commit = self.latest_commit_sha()
        base = self._request('GET', self._repo_url('/git/commits/' + base_commit))
        tree_sha = base['tree']['sha']

        entries = []
        for path, content in files.items():
            blob = self._request('POST', self._repo_url('/git/blobs'), {
                'content': base64.b64encode(content).decode('ascii'),
                'encoding': 'base64',
            })
            entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
        for path in (deletions or []):
            entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': None})

        if not entries:
            return base_commit

        tree = self._request('POST', self._repo_url('/git/trees'), {
            'base_tree': tree_sha,
            'tree': entries,
        })
        commit = self._request('POST', self._repo_url('/git/commits'), {
            'message': message,
            'tree': tree['sha'],
            'parents': [base_commit],
        })
        self._request('PATCH', self._repo_url('/git/refs/heads/' + self.branch), {
            'sha': commit['sha'],
            'force': False,
        })
        return commit['sha']

    # -------- Actions 部署状态 --------
    def latest_run(self):
        data = self._request('GET', '%s/repos/%s/actions/runs?per_page=1' % (API, self.repo))
        runs = data.get('workflow_runs') or []
        return runs[0] if runs else None

    def run_status(self, sha, timeout=600, log=print):
        deadline = time.time() + timeout
        url = '%s/repos/%s/actions/runs?per_page=20' % (API, self.repo)
        while time.time() < deadline:
            try:
                data = self._request('GET', url)
                for run in data.get('workflow_runs', []):
                    if run['head_sha'] == sha:
                        if run['status'] == 'completed':
                            return run.get('conclusion') or 'unknown'
                        log('部署进行中……（%s）' % run['status'])
                        break
            except Exception as e:
                log('查询部署状态失败：%s' % e)
            time.sleep(8)
        return 'timeout'


def _selftest():
    """无界面自检：读取仓库信息，验证 token 可用。"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from token_store import load_token
    token = load_token()
    if not token:
        print('没有保存的 token')
        return False
    api = GitHubAPI(token, 'xunshichen-2008/Pomme-project')
    sha = api.latest_commit_sha()
    print('最新 commit:', sha[:10])
    text, _ = api.get_text('_config.yml')
    print('_config.yml 行数:', len(text.splitlines()) if text else None)
    return True


if __name__ == '__main__':
    _selftest()
