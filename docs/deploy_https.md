# 공개 서버 HTTPS 적용 절차

M2 첫 공개 직전에 한 번 한다. 설정 파일은 이미 레포에 있다.

- `docker-compose-ec2.yml`: `app`(8000, 외부 비공개) + `nginx`(80·443) + `certbot`(자동 갱신)
- `deploy/nginx/templates/default.conf.template`: 80 → 443 리다이렉트, 443 → `app:8000` 프록시

## 첫 공개 조건

- [ ] `https://<도메인>/health`가 200을 반환한다
- [ ] `http://<EC2 IP>:8000/health`가 **외부에서 응답하지 않는다** (보안 그룹에서 8000을 닫았다)
- [ ] `http://<도메인>`이 `https://`로 리다이렉트된다

CI의 배포 확인 단계가 처음 두 가지를 자동으로 검사한다.

## 1. 도메인 (DuckDNS, 무료)

1. https://www.duckdns.org 에 로그인하고 서브도메인을 만든다 (예: `my-coach` → `my-coach.duckdns.org`).
2. 그 서브도메인의 IP를 EC2 퍼블릭 IP로 설정한다.
   - EC2를 중지·재시작하면 퍼블릭 IP가 바뀐다. Elastic IP를 붙이지 않았다면 재시작할 때마다 갱신해야 한다.

## 2. EC2 준비

1. 보안 그룹 인바운드: **80, 443 허용**, **8000 제거**, 22는 내 IP만.
2. `~/ai-interview-coach/.env`에 다음을 추가한다.

   ```
   APP_DOMAIN=my-coach.duckdns.org
   SECRET_KEY=<긴 무작위 문자열>
   ```

## 3. 최초 인증서 발급 (한 번만)

nginx는 인증서 파일이 있어야 뜬다. 처음에는 certbot을 standalone 모드로 직접 80 포트에 띄워 발급한다.

```bash
cd ~/ai-interview-coach
docker compose -f docker-compose-ec2.yml stop nginx
docker compose -f docker-compose-ec2.yml run --rm -p 80:80 --entrypoint certbot certbot \
  certonly --standalone -d my-coach.duckdns.org --agree-tos -m <이메일> --no-eff-email
docker compose -f docker-compose-ec2.yml up -d
```

이후 갱신은 `certbot` 컨테이너가 12시간마다 시도하고, `nginx`가 6시간마다 설정을 다시 읽어 반영한다.

## 4. GitHub Actions secret

- `APP_DOMAIN`: `my-coach.duckdns.org` (배포 확인 단계가 HTTPS로 확인한다)

## 확인

```bash
curl -s https://my-coach.duckdns.org/health
curl -s -m 5 http://<EC2 IP>:8000/health   # 응답이 없어야 한다
curl -sI http://my-coach.duckdns.org | head -1   # 301
```
