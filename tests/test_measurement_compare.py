from __future__ import annotations

from pathlib import Path

from pipetune.measurement.compare import compare_responses


def test_compare_response_computes_shared_metrics(tmp_path) -> None:
    output = tmp_path / "comparison.json"

    report = compare_responses(
        Path("tests/fixtures/measurement/before.csv"),
        Path("tests/fixtures/measurement/after.csv"),
        output,
    )

    assert output.exists()
    assert report["grid_point_count"] == 10
    assert report["average_absolute_difference_db"] > 0
    assert report["max_absolute_difference_db"] > 0
    assert report["band_summaries"]["bass"]["point_count"] > 0
    assert "sub_bass" in report["band_summaries"]
    assert "air" in report["band_summaries"]
    assert "variance_before" in report
    assert "variance_after" in report
    assert report["flatter_by_variance"] is True


def test_compare_response_reports_after_worse_by_variance(tmp_path) -> None:
    output = tmp_path / "comparison.json"

    report = compare_responses(
        Path("tests/fixtures/measurement/flat.csv"),
        Path("tests/fixtures/measurement/worse_after.csv"),
        output,
    )

    assert report["flatter_by_variance"] is False
