---
name: agent-reach
description: AI 에이전트가 트위터/X, 레딧, 인스타그램, 유튜브 자막, 깃허브, 깃허브 이슈, RSS, 넷상 문서 등을 API 비용 없이 바로 크롤링/파싱하여 읽을 수 있도록 지원하는 무제한 웹 통합 스킬
---

# Agent Reach Skill (무제한 웹 & 소셜 미디어 크롤링/파싱 스킬)

Agent Reach는 명령어 한 줄로 AI 에이전트가 유료 API 없이 주요 소셜 미디어 및 웹 콘텐츠에 접속하고 정보를 수집할 수 있도록 지원하는 오픈소스 툴입니다.

## 지원 플랫폼 & 명령 예시

- **상태 진단**: `agent-reach doctor` (채널 상태 및 미설정 항목 점검)
- **트위터/X 데이터 수집**: `agent-reach twitter search "AI 팁"`
- **레딧 帖子 조회**: `agent-reach reddit get <post_url>`
- **유튜브 자막 파싱**: `agent-reach youtube transcript <video_url>`
- **웹페이지/RSS 읽기**: `agent-reach web read <url>`

## Antigravity 사용 규칙

터미널에서 `agent-reach` 명령어를 실행하여 웹/소셜 데이터 수집 후 결과물을 분석에 활용합니다.
