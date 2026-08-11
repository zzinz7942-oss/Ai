---
name: omniroute
description: 다양한 AI 모델 프로바이더(Gemini, OpenAI, DeepSeek, Anthropic, Ollama 등) 간의 자동 폴백(Auto-Fallback), 멀티 라우팅 및 토큰 압축 라우팅 스킬
---

# OmniRoute Skill (AI 멀티 라우팅 & 자동 폴백 스킬)

이 스킬은 특정 AI 프로바이더의 API 호출 실패(Rate Limit, 429 오류, 키 만료 등) 시 다른 백업 AI 모델로 자동 폴백(Cascading Fallback)을 실행하고, AI 프롬프트와 응답 토큰을 최적화하여 안정적인 연속 실행 환경을 구축합니다.

## 주요 기능

1. **자동 프로바이더 폴백 (Auto-Fallback)**: Gemini ➔ OpenAI ➔ DeepSeek ➔ 로컬 Ollama 순으로 API 오류 시 자동 전환.
2. **토큰 압축 (Token Compression)**: 불필요한 반복 텍스트를 제거하여 API 토큰 소비 15~50% 절감.
3. **OmniRoute 게이트웨이 연동**: 로컬 프록시 게이트웨이 (`http://localhost:20128/v1`) 연동 지원.
