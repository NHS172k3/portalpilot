from app.worker import router


def test_worker_router_is_registered() -> None:
    assert router.prefix == "/worker"
