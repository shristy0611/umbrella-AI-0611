"""Generate consolidated test report."""

import os
import sys
import json
import time
import pytest
from datetime import datetime
from typing import Dict, Any, List

def run_tests() -> Dict[str, Any]:
    """Run all end-to-end tests and collect results.
    
    Returns:
        Dict[str, Any]: Test results
    """
    # Run tests and capture output
    test_output = pytest.main([
        "tests/e2e/",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "-s"
    ])
    
    return {
        "exit_code": test_output,
        "timestamp": datetime.now().isoformat()
    }

def generate_markdown_report(results: Dict[str, Any]) -> str:
    """Generate markdown report from test results.
    
    Args:
        results: Test results
        
    Returns:
        str: Markdown report
    """
    report = [
        "# UMBRELLA-AI End-to-End Test Report\n",
        f"Generated at: {datetime.now().isoformat()}\n",
        "## Test Summary\n",
        f"- Exit Code: {results['exit_code']}\n",
        f"- Status: {'Passed' if results['exit_code'] == 0 else 'Failed'}\n\n",
        "## Test Cases\n"
    ]
    
    # Add test case details
    test_cases = [
        {
            "name": "Health Checks",
            "description": "Verify all services are healthy and responding",
            "test_function": "test_health_checks"
        },
        {
            "name": "Concurrent Tasks",
            "description": "Test concurrent task processing across services",
            "test_function": "test_concurrent_tasks"
        },
        {
            "name": "Task Dependencies",
            "description": "Verify correct handling of task dependencies",
            "test_function": "test_task_dependencies"
        },
        {
            "name": "System Recovery",
            "description": "Test system recovery after service failures",
            "test_function": "test_system_recovery"
        },
        {
            "name": "Full Workflow",
            "description": "End-to-end workflow test with all components",
            "test_function": "test_full_workflow"
        }
    ]
    
    for case in test_cases:
        report.extend([
            f"### {case['name']}\n",
            f"- Description: {case['description']}\n",
            f"- Test Function: `{case['test_function']}`\n",
            "\n"
        ])
    
    # Add system information
    report.extend([
        "## System Information\n",
        f"- Python Version: {sys.version}\n",
        f"- Operating System: {os.uname().sysname} {os.uname().release}\n",
        f"- Test Directory: {os.getcwd()}\n",
        "\n"
    ])
    
    return "".join(report)

def main():
    """Generate test report."""
    try:
        # Run tests
        results = run_tests()
        
        # Generate report
        report = generate_markdown_report(results)
        
        # Write report to file
        report_path = "deployment_summary_report.md"
        with open(report_path, "w") as f:
            f.write(report)
            
        print(f"Test report generated: {report_path}")
        sys.exit(results["exit_code"])
        
    except Exception as e:
        print(f"Error generating test report: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 