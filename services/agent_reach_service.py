# -*- coding: utf-8 -*-
"""
Agent Reach 통합 서비스 (Agent Reach Service)
- agent-reach CLI 호출 및 채널 진단/데이터 수집 wrapper
"""

import subprocess
import sys

def run_agent_reach_command(cmd_args: list[str]) -> dict:
    """
    agent-reach CLI 명령어를 실행하고 결과를 반환합니다.
    """
    try:
        cmd = [sys.executable, "-m", "agent_reach.cli"] + cmd_args
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0:
            return {"success": True, "output": res.stdout}
        else:
            return {"success": False, "error": res.stderr or res.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_agent_reach_doctor() -> dict:
    """
    agent-reach doctor 상태 진단을 실행합니다.
    """
    return run_agent_reach_command(["doctor"])
