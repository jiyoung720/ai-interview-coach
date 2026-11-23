"""업로드 파일 안전 처리 (로컬 모드 전용, 설계 §4).

v1은 사용자가 보낸 파일명을 그대로 경로에 붙여 저장했다(경로 조작 가능, 같은 이름 덮어쓰기).
여기서는 저장 파일명을 uuid로 바꾸고, 크기·페이지 수·파싱 시간에 상한을 둔다.
v1 인덱스 교체 방식은 그대로 둔다. v2(M2)에서 이력서는 벡터 검색 대상이 아니므로 이 경로 자체가 바뀐다.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import BinaryIO, Callable

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}
MAX_BYTES = 5 * 1024 * 1024        # 5MB
MAX_PDF_PAGES = 20
PARSE_TIMEOUT_SECONDS = 20
_CHUNK = 64 * 1024


class UploadRejected(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def safe_display_name(filename: str | None) -> str:
    """경로 성분을 떼어낸 원래 파일 이름. 화면 표시와 v1 chunk의 source 값으로만 쓴다."""
    name = Path((filename or "").replace("\\", "/")).name.strip()
    return name or "upload"


def save_upload(stream: BinaryIO, filename: str | None, upload_dir: Path, max_bytes: int = MAX_BYTES) -> Path:
    """확장자를 확인하고 uuid 이름으로 저장한다. 크기를 넘으면 지우고 413."""
    suffix = Path(safe_display_name(filename)).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UploadRejected(400, f"지원하지 않는 형식입니다: {suffix or '(없음)'} (.md, .txt, .pdf만 지원)")

    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    written = 0
    try:
        with path.open("wb") as out:
            while chunk := stream.read(_CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    raise UploadRejected(413, f"파일은 {max_bytes // (1024 * 1024)}MB까지 올릴 수 있습니다.")
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def check_pdf_pages(path: Path, max_pages: int = MAX_PDF_PAGES) -> None:
    if path.suffix.lower() != ".pdf":
        return
    from pypdf import PdfReader

    try:
        pages = len(PdfReader(path).pages)
    except Exception as error:   # noqa: BLE001 - 깨진 PDF
        raise UploadRejected(422, "PDF를 읽을 수 없습니다.") from error
    if pages > max_pages:
        raise UploadRejected(413, f"PDF는 {max_pages}쪽까지 올릴 수 있습니다.")


def parse_with_timeout(parse: Callable[[str], str], path: Path, timeout: float = PARSE_TIMEOUT_SECONDS) -> str:
    """파싱에 시간 상한을 둔다. 넘으면 422. (스레드는 멈출 수 없어 응답만 먼저 돌려준다)"""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(parse, str(path))
    try:
        return future.result(timeout=timeout)
    except FutureTimeout as error:
        raise UploadRejected(422, "파일을 읽는 데 시간이 너무 오래 걸립니다.") from error
    except UploadRejected:
        raise
    except Exception as error:   # noqa: BLE001 - 파서 오류
        raise UploadRejected(422, "파일에서 텍스트를 읽을 수 없습니다.") from error
    finally:
        executor.shutdown(wait=False)
