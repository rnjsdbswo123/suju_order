# Synology NAS `suju_order` 프로젝트 배포 가이드

이 문서는 `suju_order` 프로젝트를 Docker를 사용하여 Synology NAS에 배포하는 전체 과정을 안내합니다.

---

### **A. 최초 배포 시**

가장 처음 NAS에 프로젝트를 배포할 때 아래 순서대로 진행합니다.

#### **1단계: 파일 업로드**

1.  로컬 PC에 있는 `suju_order` 프로젝트 폴더 전체를 NAS로 복사합니다.
2.  **위치**: `File Station`을 열어 `/volume1/docker/` 폴더 안에 업로드합니다.
3.  **최종 경로**: `/volume1/docker/suju_order`

> **중요**: 이전에 업로드한 폴더가 있다면, 충돌을 막기 위해 기존 `suju_order` 폴더를 완전히 삭제하고 새로 업로드하는 것을 권장합니다.

#### **2단계: 터미널 접속 및 폴더 이동**

PC에서 터미널을 열고 아래 명령어로 NAS에 접속한 뒤, 프로젝트 폴더로 이동합니다.

```bash
# 1. NAS 터미널 접속
ssh jejuwellbeing@192.168.0.166

# 2. 프로젝트 폴더로 이동
cd /volume1/docker/suju_order
```

#### **3단계: Docker 실행**

아래 명령어로 Docker 이미지를 만들고 컨테이너를 실행합니다.

```bash
sudo docker-compose up --build -d
```

#### **4단계: 데이터베이스 설정 (최초 1회 필수)**

새로 만들어진 데이터베이스에 테이블과 관리자 계정을 생성합니다.

```bash
# 1. 데이터베이스 테이블 생성
sudo docker-compose exec app python manage.py migrate

# 2. 관리자 계정 생성 (질문에 순서대로 답변)
sudo docker-compose exec app python manage.py createsuperuser
```

---

### **B. 애플리케이션 업데이트 시**

로컬 PC에서 코드를 수정한 후 NAS에 반영할 때 진행합니다.

1.  **파일 업로드**: 수정한 `suju_order` 폴더 전체를 NAS에 **덮어쓰기**로 다시 업로드합니다.
2.  **터미널 접속 및 폴더 이동**: 위 `A-2단계`와 동일하게 진행합니다.
3.  **Docker 업데이트**: 아래 명령어를 실행하여 변경된 내용으로 컨테이너를 다시 생성합니다.
    ```bash
    sudo docker-compose up --build -d
    ```
4.  **데이터베이스 업데이트 (필요시)**: 만약 `models.py` 파일을 수정했다면, 아래 `migrate` 명령어를 추가로 실행합니다.
    ```bash
    sudo docker-compose exec app python manage.py migrate
    ```

---

### **C. 접속 정보 및 설정**

-   **내부 네트워크 접속 주소**
    `http://192.168.0.166:8009/`

-   **외부 네트워크 접속 주소**
    `http://jejuwellbeing1.synology.me:449/`

-   **필요한 공유기 포트포워딩 규칙**
    -   **외부 포트**: `449`
    -   **내부 IP**: `192.168.0.166`
    -   **내부 포트**: `8009`
    -   **프로토콜**: `TCP`

---

### **D. 유용한 Docker 명령어**

```bash
# 실행 중인 컨테이너 목록 확인
sudo docker ps

# 컨테이너 실시간 로그 확인
sudo docker-compose logs -f

# 컨테이너 중지 및 삭제
sudo docker-compose down
```



# 업로드 후 이거하면 재빌드? 터미널 닫고 다시 열어야함..

ssh jejuwellbeing@192.168.0.166

cd /volume1/docker/suju_order


sudo docker-compose build --no-cache
sudo docker-compose up --build -d






  1. 단순 코드 수정 시 (대부분의 경우)

   * views.py, html 파일 등 파이썬 코드만 수정한 경우

   1     # 1. 수정한 코드 파일들을 서버에 업로드 (덮어쓰기)
   2 
   3     # 2. 아래 명령어로 앱을 새로 빌드하고 재시작하면 끝입니다.
   4     sudo docker-compose up --build -d

  2. 데이터베이스 모델 수정 시

   * models.py 파일을 수정하여 테이블 구조를 변경한 경우

   1     # 1. 수정한 코드 파일들을 서버에 업로드
   2 
   3     # 2. 앱을 새로 빌드하고 재시작
   4     sudo docker-compose up --build -d
   5 
   6     # 3. 앱 컨테이너 안에서 migrate 명령어 실행 (이것만 추가됩니다)
   7     sudo docker exec suju_order-app-1 python manage.py migrate
