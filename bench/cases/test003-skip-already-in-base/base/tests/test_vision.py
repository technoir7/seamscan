import pytest

from vision.model import classify


@pytest.mark.skip(reason="needs the GPU runner")
def test_classify_batch_on_gpu():
    assert len(classify(["a.png", "b.png"], device="cuda")) == 2
