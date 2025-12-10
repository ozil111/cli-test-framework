from cli_test_framework.file_comparator.factory import ComparatorFactory


def compare_binary(file1, file2, **kwargs):
    comparator = ComparatorFactory.create_comparator("binary", **kwargs)
    return comparator.compare_files(file1, file2)


def test_binary_identical(tmp_path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    data = b"\x00\x01\x02demo"
    f1.write_bytes(data)
    f2.write_bytes(data)

    result = compare_binary(f1, f2)
    assert result.identical
    assert result.differences == []


def test_binary_difference_and_similarity(tmp_path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"\x00\x01\x02demo")
    f2.write_bytes(b"\x00\x01\x03demo")

    result = compare_binary(f1, f2, similarity=True)
    assert not result.identical
    assert result.similarity is not None
    assert result.differences

