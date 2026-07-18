# Atlas GIS Map Pipeline

Atlas의 구면 격자 게임 지도를 생성·검증하고 Unreal Engine용 데이터를
내보내는 공개 QGIS/GIS 파이프라인입니다.

실제 QGIS 프로젝트, 설정, 원천 데이터, 처리 스크립트, 검증 보고서와
Unreal용 export는 `AtlasMap/` 아래에 있습니다. 프로젝트 사용법과 지도
규칙은 다음 문서에서 확인합니다.

- `AtlasMap/README.md`
- `AtlasMap/GLOBAL_MAP_RULES.md`
- `AtlasMap/AGENTS.md`

Unreal Engine 게임 프로젝트는 별도의 private 저장소
`kim-kihoon/atlas`에서 관리합니다.

## 저장소 이름 변경 안내

이 저장소의 GitHub 이름은 다음과 같이 변경되었습니다.

```text
이전: kim-kihoon/project-atlas
현재: kim-kihoon/atlas-gis
```

GitHub가 이전 URL을 새 저장소로 자동 연결하므로 기존 clone에서 당장
`pull`이나 `push`가 중단되지는 않습니다. 하지만 이전 이름을 다시
사용하거나 자동 연결에 계속 의존하지 않도록 각 컴퓨터의 `origin`을 새
주소로 갱신해야 합니다.

## 기존 컴퓨터에서 해야 할 작업

기존 `project-atlas` 로컬 폴더에서 다음 명령을 실행합니다.

```powershell
git remote -v
git remote set-url origin https://github.com/kim-kihoon/atlas-gis.git
git remote -v
git fetch --prune
git status -sb
```

SSH remote를 사용한다면 다음 주소로 변경합니다.

```powershell
git remote set-url origin git@github.com:kim-kihoon/atlas-gis.git
```

변경 후 `git remote -v`의 fetch와 push 주소가 모두 다음처럼 표시되는지
확인합니다.

```text
origin  https://github.com/kim-kihoon/atlas-gis.git (fetch)
origin  https://github.com/kim-kihoon/atlas-gis.git (push)
```

로컬 파일, 브랜치, 커밋과 작업 중인 변경 사항은 remote URL을 바꿔도
삭제되거나 초기화되지 않습니다.

## 새 컴퓨터에서 저장소 받기

이 저장소는 Public이므로 다음 중 한 가지 방법으로 복제할 수 있습니다.

GitHub CLI를 사용하는 경우:

```powershell
gh repo clone kim-kihoon/atlas-gis
cd atlas-gis
git lfs install
git lfs pull
```

일반 Git을 사용하는 경우:

```powershell
git clone https://github.com/kim-kihoon/atlas-gis.git
cd atlas-gis
git lfs install
git lfs pull
```

이 저장소는 GeoPackage, GeoJSON, ZIP, PBF와 Shapefile 등 대용량 GIS
파일을 Git LFS로 관리합니다. Git LFS가 없거나 `git lfs pull`을 실행하지
않으면 실제 데이터 대신 작은 포인터 파일만 내려받을 수 있습니다.

## 주의사항

- 이전 이름인 `project-atlas`로 새 GitHub 저장소를 만들지 않습니다.
  새 저장소가 생기면 기존 URL의 자동 연결이 끊길 수 있습니다.
- 문서나 스크립트에 저장소 URL을 추가할 때는
  `https://github.com/kim-kihoon/atlas-gis`를 사용합니다.
- `AtlasMap` 내부의 QGIS 프로젝트와 설정에는 절대경로를 저장하지 않고
  `AtlasMap/` 기준 상대경로만 사용합니다.
- QGIS 프로젝트 파일만 따로 복사하지 말고 필요한 데이터, 설정과
  스크립트를 포함한 `AtlasMap/` 구조를 유지합니다.
