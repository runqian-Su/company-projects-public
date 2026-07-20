from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "src.c_platform.app:app",
        host="127.0.0.1",
        port=8787,
        reload=False,
    )

