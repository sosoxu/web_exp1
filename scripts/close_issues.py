#!/usr/bin/env python3
"""
关闭已修复的GitHub Issue
读取open_issues.json中的Issue编号，逐个关闭
"""
import os
import sys

# 复用create_issues.py中的功能
sys.path.insert(0, os.path.dirname(__file__))
from create_issues import close_fixed_issues


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    issues_file = os.path.join(project_dir, "test-reports", "open_issues.json")

    if not os.path.exists(issues_file):
        print("没有需要关闭的Issue")
        return

    print("关闭已修复的Issues...")
    close_fixed_issues(issues_file)


if __name__ == "__main__":
    main()
