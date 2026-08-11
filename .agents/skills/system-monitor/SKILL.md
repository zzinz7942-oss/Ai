---
name: system-monitor
description: 안티그래피티 시스템 헬스 체크 및 백그라운드 태스크(Streamlit, Playwright, OmniRoute) 24시간 실시간 감시 스킬.
---

# System Health Monitor Skill

본 스킬은 안티그래피티 에이전트가 백그라운드 태스크(Uvicorn Streamlit server, Playwright chromium, OmniRoute proxy)의 정상 작동 여부를 실시간 감시하고 자동 복구하도록 지침을 제공합니다.

## 핵심 실행 규칙
1. **Streamlit 서버 복구**: `http://localhost:8502` 응답이 없을 경우 백그라운드 프로세스 재시작.
2. **AI 프로바이더 헬스 체크**: Gemini/OpenAI API 에러 발생 시 OmniRoute 로컬 게이트웨이로 1초 이내 자동 스위칭.
3. **무오류 원칙**: 에러 발생 시 숨기지 않고 100% Empiric Log Evidence에 기반하여 즉시 교정.
