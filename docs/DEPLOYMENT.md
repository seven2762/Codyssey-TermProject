# OCI Docker 배포

AskMate 백엔드는 GitHub Actions에서 Docker 이미지를 빌드해 Docker Hub의
`2hynmin/codyssey-term`에 게시한다. 배포 작업은 Tailscale에 임시 노드로 접속한 뒤
OCI Compute 인스턴스에서 해당 이미지를 실행한다.

## 배포 흐름

1. `develop` 대상 PR에서는 Docker 이미지가 빌드되는지만 검증한다.
2. 검증된 `develop`을 `main`에 병합하면 다중 아키텍처 이미지를 Docker Hub에 게시한다.
3. GitHub Actions 러너가 `tag:ci` Tailscale 임시 노드로 접속한다.
4. 러너가 OCI의 Tailscale IP로 SSH 접속해 새 컨테이너를 시작한다.
5. Docker 상태 확인이 실패하면 직전 컨테이너를 다시 시작한다.

이미지는 다음 두 태그로 게시한다.

- `2hynmin/codyssey-term:latest`
- `2hynmin/codyssey-term:sha-<Git 커밋 SHA>`

OCI에는 변경 불가능한 커밋 SHA 태그를 배포한다. `latest`는 사람이 최신 이미지를
확인하거나 수동으로 실행할 때 사용한다.

## OCI 사전 준비

OCI Compute 인스턴스에는 다음 항목이 준비되어 있어야 한다.

- Docker Engine
- Tailscale 클라이언트와 고정된 Tailscale IPv4 주소
- 비밀번호 없이 Docker 명령을 실행할 수 있는 배포용 SSH 사용자
- 배포용 SSH 공개 키
- Tailscale 인터페이스에서 SSH와 애플리케이션 포트를 허용하는 운영체제 방화벽 규칙

기본 애플리케이션 포트는 `8000`이다. 컨테이너는 공인 인터페이스가 아니라 OCI의
Tailscale IPv4 주소에만 이 포트를 게시한다. 따라서 SSH와 애플리케이션 포트를 위한
공개 OCI NSG 또는 Security List 인바운드 규칙은 추가하지 않는다.

OCI에서 다음 명령으로 배포 대상 Tailscale IPv4 주소를 확인한다.

```bash
tailscale ip -4
```

Ubuntu에서 SSH 22번과 애플리케이션 8000번을 Tailscale 인터페이스에만 허용하는 예시는
다음과 같다. 실제 SSH 포트 또는 `OCI_APP_PORT`가 다르면 해당 값을 사용한다.

```bash
sudo ufw allow in on tailscale0 to any port 22 proto tcp
sudo ufw allow in on tailscale0 to any port 8000 proto tcp
```

AI API 키 등 런타임 비밀값이 필요한 경우 OCI 인스턴스의
`/opt/askmate/.env`에 저장한다. 이 파일은 Git에 커밋하거나 GitHub Actions 로그에
출력하지 않는다. 배포용 SSH 사용자가 파일을 읽을 수 있도록 최소 권한만 부여한다.

SQLite 저장 경로와 볼륨 마운트는 DB 담당자와 경로를 합의한 뒤 별도 Issue에서
추가한다. 현재 배포는 상태 확인 API를 제공하는 stateless 컨테이너만 대상으로 한다.

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

GitHub `production` 환경에는 승인자를 지정해 `main` 병합과 실제 배포 사이에 수동
승인 단계를 둘 수 있다.

## 로컬 Docker 검증

저장소 루트에서 이미지를 빌드하고 실행한다.

```bash
docker build -t askmate-backend:local backend
docker run --rm -p 8000:8000 --name askmate-backend-local askmate-backend:local
```

다른 터미널에서 상태 확인 API를 호출한다.

```bash
curl --fail http://127.0.0.1:8000/health
```

정상 응답은 `{"status":"ok"}`이다.

## 수동 재배포

자동 배포가 실패하지 않았는데 다시 실행해야 한다면 GitHub Actions의
`Docker CI and OCI deploy` workflow를 `main` 브랜치에서 수동 실행한다. 다른
브랜치에서 수동 실행하면 이미지를 빌드하거나 OCI에 배포하지 않는다.
