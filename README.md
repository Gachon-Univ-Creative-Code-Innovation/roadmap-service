# roadmap-service
로드맵 관리 서비스

## 🧷 Git 작업 컨벤션 (Branch / Commit / PR)

### 📂 브랜치 네이밍 규칙

예시:
- `feat/GUC-31-login-api`
- `fix/GUC-27-comment-delete-bug`
- `test/GUC-40-user-service-test`

**타입 목록:**

| 타입       | 설명                       |
|------------|----------------------------|
| `feat`     | 새로운 기능 추가           |
| `fix`      | 버그 수정                  |
| `refactor` | 리팩토링 (기능 변경 없이 코드 개선) |
| `test`     | 테스트 코드 관련           |
| `hotfix`   | 긴급 수정                  |

---

### 💬 커밋 메시지 컨벤션

예시:
```
feat: 로그인 성공 시 홈 리디렉션 구현 

- 로그인 성공 시 api/home 으로 이동

JIRA: GUC-31
resolves: #12
```

> 🔹 `resolves: #12` → PR 머지 시 GitHub 이슈 자동 닫힘  
> 🔹 `JIRA: GUC-31` → Jira 티켓 번호 명시 (연동 시 자동 링크 가능)

### 🔁 작업 프로세스 요약

1. GitHub 이슈 생성 시 → Jira 티켓 & 브랜치 자동 생성
2. 브랜치로 이동해 작업 수행
3. 커밋 시 `JIRA`, `resolves` 포함
4. PR 작성 → 템플릿에 맞춰 작성
5. PR 머지 시 → GitHub 이슈 자동 닫힘
6. 이슈 닫힘 시 → Jira 상태 자동 변경 (완료)