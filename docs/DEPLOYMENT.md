# OCI Docker 배포

AskMate 백엔드는 GitHub Actions에서 Docker 이미지를 빌드해 Docker Hub의
`2hynmin/codyssey-term`에 게시한다. 배포 작업은 Tailscale에 임시 노드로 접속한 뒤
OCI Compute 인스턴스에서 해당 이미지를 실행한다.

## 배포 흐름

1. `develop`·`main` 대상 PR에서 이미지를 게시하고 OCI에 실제로 배포한다.
2. 이 배포 잡이 통과해야 PR을 머지한다. 배포가 실패하면 머지하지 않는다.
3. GitHub Actions 러너가 `tag:ci` Tailscale 임시 노드로 접속한다.
4. 러너가 OCI의 Tailscale IP로 SSH 접속해 새 컨테이너를 시작한다.
5. Docker 상태 확인이 실패하면 직전 컨테이너를 다시 시작한다.
6. PR을 `develop`에 머지하면 같은 절차로 다시 배포해 서버를 통합본으로 되돌린다.
7. `develop`을 `main`에 병합하면 같은 절차로 배포 기준을 갱신한다.

릴리스 서버가 아닌 검증용 서버이므로 머지 전 PR 코드가 OCI에서 동작한다.
OCI 컨테이너는 하나뿐이므로 `oci-production` 동시성 그룹이 배포를 순서대로 실행하며,
가장 마지막에 성공한 배포의 코드가 서버에 남는다.

`develop` 머지에서도 배포하므로, PR 검증으로 서버가 바뀐 뒤에도 머지를 마치면
서버가 통합본으로 돌아온다. 다른 PR이 그 뒤에 다시 배포하면 서버는 또 그 PR의 코드가 된다.
시연이나 평가 직전에는 `main` 배포를 마지막으로 실행한다.

이미지 태그는 실행 유형에 따라 다르다.

| 실행 유형 | 게시 태그 |
| --- | --- |
| `develop`·`main` 대상 PR | `sha-<PR head 커밋 SHA>`, `pr-<PR 번호>` |
| `develop` 푸시·수동 실행 | `sha-<Git 커밋 SHA>`, `develop` |
| `main` 푸시·수동 실행 | `sha-<Git 커밋 SHA>`, `latest` |

OCI에는 항상 변경 불가능한 `sha-` 태그를 배포한다. `latest`는 `main`의 배포 기준만 가리키므로
검증 중인 PR이나 `develop` 통합본이 덮어쓰지 않는다.
`pull_request`의 `github.sha`는 임시 병합 커밋이므로 태그에는 PR의 head 커밋 SHA를 쓴다.

포크에서 올린 PR은 `production` 환경 Secrets를 받지 못해 배포할 수 없다.
이 경우에는 이미지를 게시하지 않고 빌드 가능 여부만 확인하는 잡이 대신 실행된다.

## OCI 사전 준비

OCI Compute 인스턴스에는 다음 항목이 준비되어 있어야 한다.

- Docker Engine
- Tailscale 클라이언트와 고정된 Tailscale IPv4 주소
- 비밀번호 없이 Docker 명령을 실행할 수 있는 배포용 SSH 사용자
- 배포용 SSH 공개 키
- SSH는 Tailscale 인터페이스에만, 애플리케이션 포트는 공개로 허용하는 방화벽 규칙
- 공인 IPv4 주소와 이를 허용하는 OCI Security List 인그레스 규칙

기본 애플리케이션 포트는 `8000`이다. 컨테이너는 이 포트를 모든 인터페이스(`0.0.0.0`)에
게시하므로, 누구나 `http://<공인 IP>:8000`으로 서비스를 사용할 수 있다.
배포 접속 경로인 SSH는 계속 Tailscale로만 열어 둔다.

OCI에서 다음 명령으로 두 주소를 확인한다.

```bash
tailscale ip -4                      # 배포용 SSH 접속 주소 (OCI_HOST 시크릿)
curl -s https://ifconfig.me; echo    # 사용자에게 안내할 공인 IP
```

### 서버 방화벽

Ubuntu 기준이다. 실제 SSH 포트나 `OCI_APP_PORT`가 다르면 해당 값을 쓴다.

```bash
sudo ufw allow in on tailscale0 to any port 22 proto tcp   # SSH는 Tailscale만
sudo ufw allow 8000/tcp                                    # 애플리케이션은 공개
sudo ufw status
```

### OCI Security List 인그레스 규칙

서버 방화벽만 열어서는 접속되지 않는다. OCI 콘솔에서도 허용해야 한다.

1. `Networking > Virtual Cloud Networks`에서 인스턴스가 속한 VCN을 연다.
2. 해당 서브넷의 `Security Lists`(또는 `Network Security Groups`)를 연다.
3. `Add Ingress Rules`로 아래 규칙을 추가한다.

| 항목 | 값 |
| --- | --- |
| Stateless | No |
| Source Type | CIDR |
| Source CIDR | `0.0.0.0/0` |
| IP Protocol | TCP |
| Destination Port Range | `8000` |

SSH(22번)용 공개 규칙은 추가하지 않는다. SSH는 Tailscale 경로만 사용한다.

### 접속 확인

```bash
curl --fail http://<공인 IP>:8000/health
```

`{"status":"ok"}`가 나오면 외부에서 접속할 수 있는 상태다.
실패하면 서버 방화벽(`ufw status`)과 OCI Security List를 순서대로 확인한다.

### 통신 구간 보호

현재 공개 경로는 HTTP다. 로그인 비밀번호와 세션 쿠키가 암호화되지 않은 채 전송된다.
평가나 시연처럼 짧게 공개하는 용도라면 그대로 쓸 수 있지만, 계속 공개해 둔다면
아래처럼 HTTPS를 붙이는 편이 안전하다. 도메인을 사지 않아도 된다.

`sslip.io`는 IP가 들어간 호스트 이름을 그 IP로 되돌려주는 공개 DNS다.
`203.0.113.10.sslip.io` 같은 이름을 쓰면 Let's Encrypt 인증서를 받을 수 있다.

```bash
# 서버에서 Caddy를 리버스 프록시로 실행한다. 인증서는 자동으로 발급·갱신된다.
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
docker run -d --name askmate-proxy --restart unless-stopped \
  --network host \
  caddy:2 caddy reverse-proxy \
  --from <공인 IP를 점으로 이은 이름>.sslip.io --to 127.0.0.1:8000
```

OCI Security List에도 80·443 인그레스를 추가한다.
HTTPS로 서비스한 뒤에는 `production` 환경 Variable `SESSION_HTTPS_ONLY`를 `true`로 바꾼다.
쿠키에 `Secure` 속성이 붙어 HTTP로는 전송되지 않는다.

### 애플리케이션 환경 변수 전달

`SESSION_SECRET_KEY`가 없으면 앱이 시작하지 않아 상태 확인에 실패한다.
이 값은 서버에 직접 두지 않고 GitHub `production` 환경 Secrets에서 전달한다.

배포는 `Upload application environment to OCI` 단계에서 값을 SSH **표준 입력**으로만 보내
`~/.askmate-deploy.env`에 권한 `600`으로 저장한다. 값이 원격 프로세스 목록이나 Actions 로그에
남지 않는다. `docker run`이 이 파일을 읽은 뒤 원격 스크립트가 파일을 삭제한다.

서버의 `/opt/askmate/.env`도 계속 지원한다. 두 파일이 모두 있으면 서버 파일을 먼저 적용하고
워크플로가 전달한 값으로 덮어쓴다. 팀원이 서버에서 직접 실험할 때 이 파일을 쓸 수 있다.

동일한 `SESSION_SECRET_KEY`를 유지해야 재배포 후에도 기존 로그인 세션이 유지된다.
Secret 값을 바꾸면 모든 세션이 무효가 된다.
브라우저가 HTTPS로 접근하는 배포에서는 `SESSION_HTTPS_ONLY` Variable을 `true`로 설정한다.
현재 문서의 Tailscale IP 직접 HTTP 접근에서는 `false`를 사용한다.
쿠키 설정만으로 HTTPS가 제공되지는 않으며, 외부 공개 시에는 HTTPS 접속 경로를 마련한다.
AI 게이트웨이 키도 같은 방식으로 전달한다. 키는 Secret, 주소·모델·제한 시간은
Variable로 등록한다. 실제 키는 Git에 커밋하지 않는다.

SQLite는 기본적으로 `/app/data/askmate.db`에 저장한다. 배포는 이름 있는 Docker
볼륨 `askmate-data`를 `/app/data`에 마운트하므로 컨테이너 교체 후에도 DB 파일을 유지한다.
첫 실행 시 볼륨은 자동 생성되며, 이미지의 `/app/data`는 실행 사용자 UID 10001이 소유한다.
기존 볼륨을 재사용한다면 UID 10001의 쓰기 권한을 확인한다. 운영 중 이 볼륨을 삭제하지 않는다.
`DATABASE_PATH`를 지정한다면 `/app/data` 내부 경로를 사용한다. 다른 경로를 사용하려면
해당 경로에도 영구 저장소와 쓰기 권한이 필요하다.

현재는 DB 연결을 확인하고 없는 `users`·`chats` 테이블을 생성한다.
기존 사용자 DB에는 `chats`만 추가하며 기존 계정·기록을 삭제하지 않는다.
향후 테이블 구조를 바꾸는 배포에서는 DB 백업과 스키마 호환성을 별도로 확인한다.
이전 컨테이너로 롤백해도 공유 볼륨의 DB 내용까지 되돌아가지는 않는다.

## GitHub production 환경

저장소의 `Settings > Environments`에서 `production` 환경을 만들고 다음 Secrets를
등록한다.

| Secret | 내용 |
| --- | --- |
| `DOCKERHUB_TOKEN` | `2hynmin` 계정에서 발급한 Docker Hub access token |
| `OCI_HOST` | `tailscale ip -4`로 확인한 OCI의 Tailscale IPv4 주소 |
| `OCI_SSH_USER` | 배포용 SSH 사용자 이름 |
| `OCI_SSH_PRIVATE_KEY` | 배포용 SSH 개인 키 전체 내용 |
| `OCI_SSH_KNOWN_HOSTS` | 검증한 OCI SSH host key 한 줄 |
| `TS_OAUTH_CLIENT_ID` | Tailscale Workload Identity Federation Client ID |
| `TS_AUDIENCE` | Tailscale Workload Identity Federation Audience |
| `SESSION_SECRET_KEY` | 세션 쿠키 서명키. 아래 명령으로 생성한 값을 등록한다 |
| `AI_API_KEY` | AI 게이트웨이 API 키 |

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

세션 설정의 의미는 [계정·세션 인증 안내](AUTH.md)를 따른다.

`OCI_SSH_KNOWN_HOSTS`는 신뢰할 수 있는 환경에서 아래 명령으로 얻고, OCI에서 확인한
host key fingerprint와 일치하는지 검증한 뒤 등록한다.

```bash
ssh-keyscan -p 22 <OCI_HOST>
```

Tailscale 관리 콘솔에서는 GitHub Actions 임시 노드가 사용할 `tag:ci`를 만들고,
Workload Identity Federation credential에 `auth_keys` scope와 해당 태그를 허용한다.
Tailnet 접근 정책은 `tag:ci`에서 이 OCI 인스턴스의 SSH 포트로 향하는 연결만 허용한다.
워크플로 실행이 끝나면 임시 노드는 Tailnet에서 자동으로 제거된다.

필요하면 같은 `production` 환경에 다음 Variables를 등록한다.

| Variable | 기본값 | 설명 |
| --- | --- | --- |
| `OCI_SSH_PORT` | `22` | OCI SSH 포트 |
| `OCI_APP_PORT` | `8000` | OCI의 Tailscale IPv4 주소에 게시할 애플리케이션 포트 |
| `SESSION_MAX_AGE` | `3600` | 로그인 후 세션 유효기간(초). 양의 정수 |
| `SESSION_HTTPS_ONLY` | `false` | HTTPS 배포에서만 `true`로 설정 |
| `AI_BASE_URL` | 없음 | OpenAI 호환 게이트웨이 주소. `/chat/completions` 앞까지 |
| `AI_MODEL` | 없음 | 게이트웨이가 제공하는 모델 이름 |
| `AI_TIMEOUT` | `30` | AI 응답 제한 시간(초). 양수 |

`AI_BASE_URL`과 `AI_MODEL`은 기본값이 없으므로 반드시 등록한다.
값이 없으면 앱이 시작하지 않아 배포가 실패한다.

세션·AI 설정은 배포 전에 형식을 검증한다.
잘못된 값이면 컨테이너를 교체하기 전에 워크플로가 실패한다.

GitHub `production` 환경에는 승인자를 지정해 실제 배포 앞에 수동 승인 단계를 둘 수
있다. 다만 현재는 PR 단계에서도 배포하므로, 승인자를 지정하면 모든 PR이 승인을 기다린다.

## 로컬 Docker 검증

저장소 루트에서 이미지를 빌드하고 실행한다.

```bash
docker build -t askmate-backend:local backend
docker run --rm -p 8000:8000 --env-file backend/.env --mount type=volume,source=askmate-data-local,target=/app/data --name askmate-backend-local askmate-backend:local
```

다른 터미널에서 상태 확인 API를 호출한다.

```bash
curl --fail http://127.0.0.1:8000/health
```

정상 응답은 `{"status":"ok"}`이다.

`backend/.env`에 로컬 테스트용 키를 먼저 설정한다. 기본 DB 경로는 볼륨의 `/app/data/askmate.db`이다.
화면은 `/login`, `/signup`, `/chat`, `/history`에서 확인한다. `/chat`, `/history`는 로그인 후 접근한다.
DB 영구 저장 검증은 위 테스트 전용 `askmate-data-local` 볼륨으로 진행한다.
임시 확인용 테이블·레코드를 넣고 컨테이너만 종료한 뒤, 동일한 볼륨으로 다시 실행해
기록이 남아 있는지 확인한다. 운영 볼륨 `askmate-data`에 검증 데이터를 넣지 않는다.
서버 프로세스 재시작 검증과 Docker 컨테이너 교체 검증은 별개로 수행한다.

## 수동 재배포

자동 배포가 실패하지 않았는데 다시 실행해야 한다면 GitHub Actions의
`Docker CI and OCI deploy` workflow를 `main` 또는 `develop` 브랜치에서 수동 실행한다.
다른 브랜치에서 수동 실행하면 이미지를 빌드하거나 OCI에 배포하지 않는다.

PR 배포로 서버에 남은 코드를 되돌리려면 `develop` 또는 `main`에서 이 workflow를 수동 실행한다.

```bash
gh workflow run "Docker CI and OCI deploy" --ref develop
gh workflow run "Docker CI and OCI deploy" --ref main
```
