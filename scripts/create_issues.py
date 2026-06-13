#!/usr/bin/env python3
"""
GitHub Issue提交脚本
读取测试报告中的bug清单，自动提交为GitHub Issue
修复后可通过 close_issues.py 关闭Issue
"""
import os
import json
import argparse
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER = "sosoxu"
REPO_NAME = "web_exp1"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"


def get_existing_issues():
    """获取已打开的Issues"""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(
        f"{GITHUB_API}/issues?state=open&labels=bug",
        headers=headers
    )
    if response.status_code == 200:
        return {issue["title"]: issue["number"] for issue in response.json()}
    return {}


def create_issue(title, body, labels=["bug"]):
    """创建GitHub Issue"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "title": title,
        "body": body,
        "labels": labels
    }
    response = requests.post(f"{GITHUB_API}/issues", headers=headers, json=data)
    if response.status_code == 201:
        issue = response.json()
        print(f"  ✅ Issue #{issue['number']} 已创建: {issue['html_url']}")
        return issue["number"]
    else:
        print(f"  ❌ 创建Issue失败: {response.status_code} {response.text}")
        return None


def close_issue(issue_number, comment="Bug已修复，关闭Issue"):
    """关闭GitHub Issue"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    # 添加评论
    requests.post(
        f"{GITHUB_API}/issues/{issue_number}/comments",
        headers=headers,
        json={"body": comment}
    )
    # 关闭Issue
    response = requests.patch(
        f"{GITHUB_API}/issues/{issue_number}",
        headers=headers,
        json={"state": "closed"}
    )
    if response.status_code == 200:
        print(f"  ✅ Issue #{issue_number} 已关闭")
    else:
        print(f"  ❌ 关闭Issue失败: {response.status_code}")


def create_issues_from_bugs(bugs_file):
    """从bug清单创建Issues"""
    if not os.path.exists(bugs_file):
        print(f"Bug清单文件不存在: {bugs_file}")
        return []

    with open(bugs_file) as f:
        bugs = json.load(f)

    if not bugs:
        print("没有Bug需要提交")
        return []

    existing = get_existing_issues()
    created_issues = []

    for bug in bugs:
        title = f"[Bug] {bug['source']}: {bug['test_name']}"
        # 检查是否已存在
        if title in existing:
            print(f"  ⏭️ Issue已存在: #{existing[title]} - {title}")
            created_issues.append(existing[title])
            continue

        body = f"""## Bug描述

**来源**: {bug['source']}
**测试用例**: `{bug['test_name']}`

### 错误信息

```
{bug['message']}
```

---
*此Issue由测试报告自动生成，修复后请关闭*
"""
        issue_number = create_issue(title, body)
        if issue_number:
            created_issues.append(issue_number)

    # 保存已创建的Issue编号
    issues_file = os.path.join(os.path.dirname(bugs_file), "open_issues.json")
    with open(issues_file, "w") as f:
        json.dump(created_issues, f)

    print(f"\n共处理 {len(bugs)} 个Bug，创建了 {len(created_issues)} 个Issue")
    return created_issues


def close_fixed_issues(issues_file):
    """关闭已修复的Issues"""
    if not os.path.exists(issues_file):
        print(f"Issue列表文件不存在: {issues_file}")
        return

    with open(issues_file) as f:
        issue_numbers = json.load(f)

    for num in issue_numbers:
        close_issue(num, comment="Bug已修复，自动关闭Issue")

    # 清空文件
    os.remove(issues_file)
    print(f"\n共关闭 {len(issue_numbers)} 个Issue")


def main():
    parser = argparse.ArgumentParser(description="GitHub Issue管理工具")
    parser.add_argument("action", choices=["create", "close"], help="操作: create-创建Issue, close-关闭Issue")
    parser.add_argument("--bugs-file", default=None, help="Bug清单文件路径")
    parser.add_argument("--issues-file", default=None, help="Issue列表文件路径")

    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(project_dir, "test-reports")

    if args.action == "create":
        bugs_file = args.bugs_file or os.path.join(reports_dir, "bugs.json")
        create_issues_from_bugs(bugs_file)
    elif args.action == "close":
        issues_file = args.issues_file or os.path.join(reports_dir, "open_issues.json")
        close_fixed_issues(issues_file)


if __name__ == "__main__":
    main()
