import subprocess
import hashlib
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS = 8  # 可根据机器核心数自行调整

def run_git(cmd, repo_path):
    result = subprocess.run(
        cmd, cwd=repo_path, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERR] {' '.join(cmd)}: {result.stderr}")
    return result

def parse_git_date(date_str):
    # e.g. Thu Jul 17 16:18:28 2025 +0800
    try:
        dt = datetime.datetime.strptime(date_str[:-6], "%a %b %d %H:%M:%S %Y")
        # 只保留年月日时分秒
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"date parse error: {e}, origin: {date_str}")
        return date_str

def get_commit_list(repo_path, branch, start_commit, check_all):
    if check_all:
        cmd = ['git', 'log', '--pretty=format:%H|%an|%ad|%s', f'{start_commit}^..{branch}']
        print(f"Running: git log {start_commit}^..{branch}")
    else:
        cmd = ['git', 'log', '--pretty=format:%H|%an|%ad|%s', '-1', start_commit]
        print(f"Running: git log -1 {start_commit}")
    res = run_git(cmd, repo_path)
    print(f"git log output:\n{res.stdout}")
    commits = []
    for line in res.stdout.strip().split('\n'):
        if line:
            parts = line.split('|', 3)
            date_fmt = parse_git_date(parts[2])
            commits.append({
                "commit": parts[0],
                "author": parts[1],
                "date": date_fmt,
                "message": parts[3] if len(parts) > 3 else ''
            })
    print(f"Total commits fetched: {len(commits)}")
    return commits

def get_commit_diff_hash(repo_path, commit_id):
    """
    获取commit的diff内容（去除meta行），并计算SHA1 hash。
    支持二进制内容，不会因为utf8异常报错。
    """
    cmd = ['git', 'show', '--format=', '-w', commit_id]
    res = subprocess.run(cmd, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"[ERR] {commit_id}: {res.stderr.decode('utf-8', errors='ignore')}")
        return None
    lines = []
    for l in res.stdout.splitlines():
        try:
            line = l.decode('utf-8')
            if not line.startswith("index") and not line.startswith("@@"):
                lines.append(l)
        except UnicodeDecodeError:
            # 处理二进制diff，直接追加bytes
            lines.append(l)
    diff_bytes = b'\n'.join(lines)
    hashval = hashlib.sha1(diff_bytes).hexdigest()
    return hashval

def build_branch_diffhash_map(repo_path, branch, max_commits=2000):
    """
    获取目标分支最近max_commits个提交，批量计算每个diff hash，返回hash->commit_id的字典。
    """
    cmd = ['git', 'log', branch, '--no-merges', '--format=%H', f'-n{max_commits}']
    res = run_git(cmd, repo_path)
    commit_ids = res.stdout.strip().splitlines()
    hash_map = {}
    print(f"目标分支 {branch} 共{len(commit_ids)}个commit待处理(diff hash)...")

    def compute_hash(commit_id):
        h = get_commit_diff_hash(repo_path, commit_id)
        return (commit_id, h)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_commit = {executor.submit(compute_hash, cid): cid for cid in commit_ids}
        for future in as_completed(future_to_commit):
            commit_id, h = future.result()
            if h:
                hash_map[h] = commit_id
    print(f"目标分支diff hash表构建完成: {len(hash_map)} 条")
    return hash_map

def get_src_commit_diff_hashes(repo_path, src_commits):
    """
    源分支的提交也批量算diff hash，返回 {commit_id: diff_hash}
    """
    def compute_hash(commit):
        diff_hash = get_commit_diff_hash(repo_path, commit["commit"])
        return (commit["commit"], diff_hash)

    result = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_commit = {executor.submit(compute_hash, commit): commit for commit in src_commits}
        for future in as_completed(future_to_commit):
            commit_id, diff_hash = future.result()
            result[commit_id] = diff_hash
    return result

def compare_commits_by_diff(repo_path, source_branch, target_branch, start_commit, check_all):
    # 1. 源分支提交列表
    src_commits = get_commit_list(repo_path, source_branch, start_commit, check_all)
    print(f"源分支{source_branch}待比对提交数: {len(src_commits)}")
    if not src_commits:
        return [], [], 0

    # 2. 目标分支diff hash表
    tgt_diff_hash_map = build_branch_diffhash_map(repo_path, target_branch)
    # 3. 源分支所有提交也批量生成diff hash
    src_commit_hash_map = get_src_commit_diff_hashes(repo_path, src_commits)

    matched, unmatched = [], []
    for commit in src_commits:
        diff_hash = src_commit_hash_map.get(commit["commit"])
        tgt_commit = tgt_diff_hash_map.get(diff_hash)
        if diff_hash and tgt_commit:
            # 匹配到了目标分支，返回目标分支的commit id
            commit_with_tgt = {**commit, "target_commit": tgt_commit}
            matched.append(commit_with_tgt)
        else:
            unmatched.append(commit)

    print(f"对比完成。目标分支已包含: {len(matched)}，未包含: {len(unmatched)}")
    return matched, unmatched, len(src_commits)