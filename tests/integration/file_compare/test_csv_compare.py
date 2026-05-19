from cli_test_framework.file_comparator.factory import ComparatorFactory


def compare_csv(file1, file2, **kwargs):
    comparator = ComparatorFactory.create_comparator("csv", **kwargs)
    compare_kwargs = {
        key: kwargs[key]
        for key in ("start_line", "end_line", "start_column", "end_column")
        if key in kwargs
    }
    return comparator.compare_files(file1, file2, **compare_kwargs)


def test_csv_identical_files(tmp_path):
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    content = "id,name\n1,Ada\n2,Grace\n"
    file1.write_text(content, encoding="utf-8")
    file2.write_text(content, encoding="utf-8")

    result = compare_csv(file1, file2)

    assert result.identical
    assert result.differences == []


def test_csv_cell_difference(tmp_path):
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,name\n1,Ada\n", encoding="utf-8")
    file2.write_text("id,name\n1,Grace\n", encoding="utf-8")

    result = compare_csv(file1, file2)

    assert not result.identical
    diff = result.differences[0]
    assert diff.diff_type == "cell_mismatch"
    assert diff.position == "row 2, column 2"
    assert diff.expected == "Ada"
    assert diff.actual == "Grace"


def test_csv_row_and_column_count_differences(tmp_path):
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,name\n1,Ada\n2,Grace\n", encoding="utf-8")
    file2.write_text("id,name,role\n1,Ada,admin\n", encoding="utf-8")

    result = compare_csv(file1, file2)

    assert not result.identical
    diff_types = {diff.diff_type for diff in result.differences}
    assert "row_count_mismatch" in diff_types
    assert "column_count_mismatch" in diff_types


def test_csv_column_range_limits_scope(tmp_path):
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,name,status\n1,Ada,old\n", encoding="utf-8")
    file2.write_text("id,name,status\n1,Ada,new\n", encoding="utf-8")

    result = compare_csv(file1, file2, start_column=0, end_column=1)

    assert result.identical


def test_csv_numeric_tolerance_within_range(tmp_path):
    """Numeric cells within tolerance should be treated as equal"""
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,value\n1,1.000001\n2,3.0\n", encoding="utf-8")
    file2.write_text("id,value\n1,1.0\n2,3.00001\n", encoding="utf-8")

    result = compare_csv(file1, file2, rtol=1e-5, atol=1e-5)

    assert result.identical
    assert result.differences == []


def test_csv_numeric_tolerance_exceeded(tmp_path):
    """Numeric cells exceeding tolerance should be reported as mismatch"""
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,value\n1,1.0\n", encoding="utf-8")
    file2.write_text("id,value\n1,2.0\n", encoding="utf-8")

    result = compare_csv(file1, file2, rtol=1e-5, atol=1e-8)

    assert not result.identical
    diff = result.differences[0]
    assert diff.diff_type == "cell_mismatch"
    assert diff.expected == "1.0"
    assert diff.actual == "2.0"


def test_csv_numeric_tolerance_mixed_with_string(tmp_path):
    """Non-numeric cells should still use string comparison even with tolerance enabled"""
    file1 = tmp_path / "a.csv"
    file2 = tmp_path / "b.csv"
    file1.write_text("id,name,value\n1,Ada,1.0\n", encoding="utf-8")
    file2.write_text("id,name,value\n1,Grace,1.000001\n", encoding="utf-8")

    result = compare_csv(file1, file2, rtol=1e-5, atol=1e-5)

    assert not result.identical
    # Only the string mismatch should be reported; numeric value is within tolerance
    diff_types = [d.diff_type for d in result.differences]
    assert "cell_mismatch" in diff_types
    string_diffs = [d for d in result.differences if d.diff_type == "cell_mismatch"]
    assert any(d.expected == "Ada" and d.actual == "Grace" for d in string_diffs)
