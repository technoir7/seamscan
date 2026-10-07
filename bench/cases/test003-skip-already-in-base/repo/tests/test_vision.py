import pytest

from vision.model import classify


@pytest.mark.skip(reason="needs the GPU runner")
def test_classify_batch_on_gpu():
    assert len(classify(["a.png", "b.png"], device="cuda")) == 2


def test_classify_single_on_cpu():
    assert classify(["a.png"], device="cpu")[0].label
