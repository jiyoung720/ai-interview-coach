# 앱 실행 설정. 환경변수에서 한 번 읽어 Settings 객체로 넘긴다.
#
# APP_MODE 기본값이 demo인 이유: 배포 설정에서 모드를 빠뜨려도 v1 엔드포인트(소유자 구분 없음)가
# 공개 서버에 열리지 않게 하기 위해서다. local은 명시해야만 켜진다 (설계 §2.5).
import os
from dataclasses import dataclass
from pathlib import Path

VALID_MODES = ("demo", "local")


class ConfigError(RuntimeError):
    """기동을 막아야 하는 설정 오류."""


@dataclass(frozen=True)
class Settings:
    app_mode: str = "demo"
    secret_key: str | None = None
    data_dir: Path = Path("data")

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"

    @property
    def is_local(self) -> bool:
        return self.app_mode == "local"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    def validate(self) -> "Settings":
        if self.app_mode not in VALID_MODES:
            raise ConfigError(f"APP_MODE는 {VALID_MODES} 중 하나여야 합니다: {self.app_mode!r}")
        # 데모 서버는 owner_id 쿠키 서명에 비밀키가 필요하다. 없으면 아예 뜨지 않는다.
        if self.is_demo and not self.secret_key:
            raise ConfigError("데모 모드에는 SECRET_KEY가 필요합니다.")
        return self


def load_settings(env: dict | None = None) -> Settings:
    """환경변수에서 설정을 읽어 검증한다. 테스트는 env를 직접 넘긴다."""
    if env is None:
        from dotenv import load_dotenv

        load_dotenv()   # 로컬 실행 시 .env의 APP_MODE·SECRET_KEY를 읽는다
        env = os.environ
    return Settings(
        app_mode=(env.get("APP_MODE") or "demo").strip().lower(),
        secret_key=env.get("SECRET_KEY") or None,
        data_dir=Path(env.get("DATA_DIR") or "data"),
    ).validate()
