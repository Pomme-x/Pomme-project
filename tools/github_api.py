# -*- coding: utf-8 -*-
"""用 GitHub REST API 直接上传文件（不需要本机安装 git）。

一次上传 = 一个 commit（Git Data API），提交后 GitHub Actions 自动部署。
"""

import base64
import json
import threading
import time
import urllib.error
import urllib.request

API = 'https://api.github.com'
UA = 'PommeTool/1.0'
_COMMIT_LOCK = threading.Lock()


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

    # -------- 仓库 / 文件浏览 --------
    def get_repo(self):
        return self._request('GET', self._repo_url())

    def list_dir(self, path=''):
        path = path.strip('/')
        suffix = '/contents' + (('/' + path) if path else '') + '?ref=' + self.branch
        try:
            data = self._request('GET', self._repo_url(suffix))
        except RuntimeError as e:
            if '404' in str(e):
                return []
            raise
        if isinstance(data, dict):
            return [data]
        return data

    def get_pages(self):
        try:
            return self._request('GET', self._repo_url('/pages'))
        except RuntimeError as e:
            if '404' in str(e):
                return None
            raise

    def create_pages(self):
        return self._request('POST', self._repo_url('/pages'), {'build_type': 'workflow'})

    def set_description(self, text):
        return self._request('PATCH', self._repo_url(), {'description': text})

    def rename_repo(self, new_name):
        """重命名仓库，返回新 full_name。"""
        data = self._request('PATCH', self._repo_url(), {'name': new_name})
        self.repo = data['full_name']
        return data['full_name']

    # -------- 一次提交多个文件 --------
    def commit_files(self, files, message, deletions=None, retries=3):
        """files: {path: bytes}；deletions: 需要删除的 path 列表。返回 commit sha。

        GitHub 的 ref 更新是乐观锁：如果同一时间别的地方（另一个工具窗口、网页、
        或者上一次操作）也在提交，就会报 "Update is not a fast forward"。
        这里会自动重新取最新提交并重试，避免用户看到这个错误。
        """
        last_err = None
        for attempt in range(retries):
            try:
                with _COMMIT_LOCK:
                    return self._commit_once(files, message, deletions)
            except RuntimeError as e:
                msg = str(e)
                if ('fast forward' in msg or 'non-fast-forward' in msg
                        or '409' in msg or '422' in msg):
                    last_err = e
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise
        raise RuntimeError('保存冲突：同时有另一个提交在写入，已自动重试 %d 次仍失败，'
                           '请稍后再点一次。原始错误：%s' % (retries, last_err))

    def _commit_once(self, files, message, deletions=None):
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
