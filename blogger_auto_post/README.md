# 📝 Google Blogger 자동 업로드 + 이미지 자동 첨부 + AI 자기검토 시스템

마크다운 블로그 글을 읽어 AI 자기검토/클리셰 자동 교정을 수행한 후, 이미지를 자동으로 첨부하여 Google Blogger에 업로드/수정하는 파이프라인입니다.

---

## 🔥 핵심 기능

1. **🤖 AI 자동 자기검토 및 클리셰 교정 (기본 자동 실행)**:
   - 발행 직전 Gemini 2.5 Flash가 글을 스스로 검토하여 아래 6가지 항목을 자동 재작성합니다:
     - 팁 박스 등 중복된 구조적 패턴 다변화
     - AI 특유 상투 표현("현대 문명의 쌀", "~에 대해 알아보겠습니다" 등) 완전 제거
     - 기계적 3문장 결론 구조 탈피 & 리듬감 있는 서술
     - 수치/통계 정보에 객관적 출처 뉘앙스 추가
     - AI스러운 엔딩 대신 독자 질문형/개방형 마무리 전환
     - 문법 및 오타 자동 교정
   - **로그 남김**: `logs/review_before.md`, `logs/review_after.md`, `logs/review_summary.txt`에 변경 전/후 기록.

2. **⏩ 자기검토 스킵 옵션 (`--skip-review`)**:
   - 원할 경우 `--skip-review` 옵션을 추가해 자기검토 단계를 건너뛸 수 있습니다.

3. **📝 기존 포스트 수정 기능 (`--edit <POST_ID>`)**:
   - `post_content.md` 수정 후 `--edit <포스트ID>` 옵션을 주면 새 글 생성이 아닌 기존 글을 업데이트합니다.

4. **🔑 Pure Console OAuth 2.0 인증**:
   - 로컬 서버나 브라우저 자동 오픈 없이 터미널 텍스트 URL로 깔끔하게 인증.

---

## 🚀 사용 명령어

### 1. 새 글 작성 (AI 자기검토 자동 수행)
```powershell
python main.py --no-drive
```

### 2. 기존 글 수정 (AI 자기검토 자동 수행)
```powershell
python main.py --no-drive --edit 8709539800043420726
```

### 3. AI 자기검토 건너뛰고 빠른 업로드
```powershell
python main.py --no-drive --skip-review
```

### 4. 실시간 트렌드 + 어조 반영 AI 프롬프트 생성
```powershell
python main.py --generate-prompt "반도체"
```
