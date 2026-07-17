# Security & Environment Variables

## 절대 금지 사항
- API 키, 토큰, 비밀번호, DB 연결 문자열을 소스코드에 **하드코딩 금지**.
- 절대 경로(e.g., `C:\Users\...`, `/home/...`)를 코드에 **하드코딩 금지**.
- `.env`, `config.json`, `credentials.json` 등 시크릿 파일을 **열거나 수정 금지**.
  내용을 참조해야 할 경우, 파일의 *존재 여부*와 *키 이름*만 확인할 것.

## 환경변수 사용 표준
- Python: `python-dotenv` 또는 `os.environ.get()` 사용.
  ```python
  import os
  API_KEY = os.environ.get("MY_API_KEY")
  if not API_KEY:
      raise EnvironmentError("MY_API_KEY is not set.")
  ```
- Node.js: `dotenv` 패키지 또는 `process.env.MY_API_KEY` 사용.

## .gitignore 필수 항목
아래 항목이 반드시 `.gitignore`에 포함되어 있는지 확인할 것:
```
.env
*.env.*
config.json
credentials.json
*.pem
*.key
*.token
__pycache__/
*.pyc
node_modules/
```

## 민감 정보 노출 감지 시
코드에서 위 항목에 해당하는 내용이 발견되면 즉시 수정을 제안하고, 커밋 전에
반드시 사용자에게 경고할 것.
