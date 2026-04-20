"""
python -m app.export_openapi
  → ../shared/openapi.json 에 OpenAPI 스펙을 기록한다.

FE 가 openapi-typescript 로 타입을 자동 생성하기 위해 사용한다.
"""
import json
import sys
from pathlib import Path


def main() -> None:
    # main.py 를 import 하면 lifespan 없이 app 객체만 생성됨
    from app.main import app

    spec = app.openapi()

    output_path = Path(__file__).parent.parent.parent / "shared" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OpenAPI spec exported to {output_path}", file=sys.stderr)
    # stdout 에도 출력 (파이프 연결 시 사용). Windows 콘솔 인코딩 안전을 위해 ensure_ascii=True
    sys.stdout.buffer.write(
        json.dumps(spec, ensure_ascii=True, indent=2).encode("utf-8")
    )


if __name__ == "__main__":
    main()
