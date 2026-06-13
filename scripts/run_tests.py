#!/usr/bin/env python3
"""
测试报告生成脚本
运行所有测试，生成Markdown格式的测试报告，包含bug清单
"""
import os
import sys
import json
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_DIR, "test-reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def run_backend_tests():
    """运行后端测试"""
    backend_dir = os.path.join(PROJECT_DIR, "backend")
    venv_python = os.path.join(backend_dir, "venv", "bin", "python")

    # 安装测试依赖
    subprocess.run([
        venv_python, "-m", "pip", "install", "-q",
        "pytest", "pytest-asyncio", "pytest-json-report"
    ], cwd=backend_dir)

    # 创建测试数据库
    try:
        subprocess.run([
            "psql", "-h", "localhost", "-U", "postgres",
            "-c", "CREATE DATABASE param_experiment_test;"
        ], capture_output=True, timeout=10)
    except Exception:
        pass

    # 运行测试
    result = subprocess.run([
        venv_python, "-m", "pytest",
        "tests/", "-v",
        "--json-report",
        "--json-report-file=" + os.path.join(REPORTS_DIR, "backend-results.json"),
        "--json-report-indent=2"
    ], cwd=backend_dir, capture_output=True, text=True, timeout=300,
        env={
            **os.environ,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "param_experiment_test",
            "SQLITE_DB_PATH": os.path.join(PROJECT_DIR, "data", "geomods_2.0.db"),
            "DEEPSEEK_API_KEY": "test-key"
        }
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "results_file": os.path.join(REPORTS_DIR, "backend-results.json")
    }


def run_frontend_tests():
    """运行前端测试"""
    frontend_dir = os.path.join(PROJECT_DIR, "frontend")
    result = subprocess.run([
        "npm", "run", "test:report"
    ], cwd=frontend_dir, capture_output=True, text=True, timeout=300)

    # 读取结果
    results_file = os.path.join(frontend_dir, "test-results.json")
    frontend_results = {}
    if os.path.exists(results_file):
        with open(results_file) as f:
            frontend_results = json.load(f)
        # 复制到报告目录
        import shutil
        shutil.copy2(results_file, os.path.join(REPORTS_DIR, "frontend-results.json"))

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "results": frontend_results
    }


def parse_backend_results(results_file):
    """解析后端测试结果"""
    if not os.path.exists(results_file):
        return {"total": 0, "passed": 0, "failed": 0, "errors": [], "tests": []}

    with open(results_file) as f:
        data = json.load(f)

    tests = []
    for test in data.get("tests", []):
        tests.append({
            "name": test.get("nodeid", ""),
            "outcome": test.get("outcome", "unknown"),
            "duration": test.get("duration", 0),
            "message": ""
        })
        if test["outcome"] in ("failed", "error"):
            # 提取错误信息
            call_info = test.get("call", {})
            if call_info:
                tests[-1]["message"] = call_info.get("longrepr", "")

    summary = data.get("summary", {})
    return {
        "total": summary.get("total", len(tests)),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": [],
        "tests": tests
    }


def parse_frontend_results(results):
    """解析前端测试结果"""
    if not results:
        return {"total": 0, "passed": 0, "failed": 0, "errors": [], "tests": []}

    test_results = results.get("testResults", [])
    tests = []
    total = 0
    passed = 0
    failed = 0

    for suite in test_results:
        for assertion in suite.get("assertionResults", []):
            total += 1
            status = assertion.get("status", "unknown")
            if status == "passed":
                passed += 1
            else:
                failed += 1
            tests.append({
                "name": assertion.get("fullName", assertion.get("ancestorTitles", [""])[-1]),
                "outcome": status,
                "duration": assertion.get("duration", 0),
                "message": "\n".join(
                    f.get("message", "") for f in assertion.get("failureMessages", [])
                ) if status != "passed" else ""
            })

    return {"total": total, "passed": passed, "failed": failed, "errors": [], "tests": tests}


def generate_report(backend_result, frontend_result):
    """生成Markdown测试报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backend_data = parse_backend_results(backend_result["results_file"])
    frontend_data = parse_frontend_results(frontend_result.get("results"))

    all_tests = []
    all_tests.extend([{"source": "backend", **t} for t in backend_data["tests"]])
    all_tests.extend([{"source": "frontend", **t} for t in frontend_data["tests"]])

    total = backend_data["total"] + frontend_data["total"]
    passed = backend_data["passed"] + frontend_data["passed"]
    failed = backend_data["failed"] + frontend_data["failed"]
    failed_tests = [t for t in all_tests if t["outcome"] in ("failed", "error")]

    # 生成报告
    report = f"""# 测试报告

**生成时间**: {now}
**测试总数**: {total}
**通过**: {passed}
**失败**: {failed}
**通过率**: {(passed/total*100) if total > 0 else 0:.1f}%

---

## 1. 后端测试结果

| 指标 | 数值 |
|------|------|
| 总数 | {backend_data['total']} |
| 通过 | {backend_data['passed']} |
| 失败 | {backend_data['failed']} |

### 后端测试用例详情

| # | 测试名 | 结果 | 耗时(s) |
|---|--------|------|---------|
"""

    for i, t in enumerate(backend_data["tests"], 1):
        status = "✅ 通过" if t["outcome"] == "passed" else "❌ 失败"
        report += f"| {i} | `{t['name']}` | {status} | {t['duration']:.3f} |\n"

    report += f"""
## 2. 前端测试结果

| 指标 | 数值 |
|------|------|
| 总数 | {frontend_data['total']} |
| 通过 | {frontend_data['passed']} |
| 失败 | {frontend_data['failed']} |

### 前端测试用例详情

| # | 测试名 | 结果 |
|---|--------|------|
"""

    for i, t in enumerate(frontend_data["tests"], 1):
        status = "✅ 通过" if t["outcome"] == "passed" else "❌ 失败"
        report += f"| {i} | `{t['name']}` | {status} |\n"

    # Bug清单
    report += f"""
---

## 3. Bug清单

"""

    if failed_tests:
        report += f"共发现 **{len(failed_tests)}** 个问题：\n\n"
        for i, t in enumerate(failed_tests, 1):
            report += f"""### Bug #{i}

- **来源**: {t['source']}
- **测试用例**: `{t['name']}`
- **状态**: ❌ 未修复
- **错误信息**:
```
{t['message'][:500] if t['message'] else '无详细信息'}
```

"""
    else:
        report += "🎉 未发现Bug，所有测试通过！\n"

    # 保存报告
    report_file = os.path.join(REPORTS_DIR, f"test-report-{timestamp}.md")
    with open(report_file, "w") as f:
        f.write(report)

    # 同时保存最新报告
    latest_file = os.path.join(REPORTS_DIR, "latest.md")
    with open(latest_file, "w") as f:
        f.write(report)

    # 保存bug清单为JSON（供Issue提交脚本使用）
    bugs = []
    for i, t in enumerate(failed_tests, 1):
        bugs.append({
            "id": i,
            "source": t["source"],
            "test_name": t["name"],
            "message": t["message"][:500] if t["message"] else ""
        })

    bugs_file = os.path.join(REPORTS_DIR, "bugs.json")
    with open(bugs_file, "w") as f:
        json.dump(bugs, f, ensure_ascii=False, indent=2)

    print(f"\n测试报告已生成: {report_file}")
    print(f"Bug清单已保存: {bugs_file}")
    print(f"\n总测试: {total}, 通过: {passed}, 失败: {failed}")

    return report_file, bugs


def main():
    print("=" * 60)
    print("运行测试并生成报告")
    print("=" * 60)

    # 运行后端测试
    print("\n>>> 运行后端测试...")
    backend_result = run_backend_tests()
    print(backend_result["stdout"][-2000:] if len(backend_result["stdout"]) > 2000 else backend_result["stdout"])

    # 运行前端测试
    print("\n>>> 运行前端测试...")
    frontend_result = run_frontend_tests()
    print(frontend_result["stdout"][-2000:] if len(frontend_result["stdout"]) > 2000 else frontend_result["stdout"])

    # 生成报告
    print("\n>>> 生成测试报告...")
    report_file, bugs = generate_report(backend_result, frontend_result)

    if bugs:
        print(f"\n⚠️ 发现 {len(bugs)} 个Bug，请运行 scripts/create_issues.py 提交Issue")
    else:
        print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    main()
