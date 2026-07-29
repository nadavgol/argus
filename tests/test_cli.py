import json

from nhi_engine.cli import main


def test_classify_end_to_end(tmp_path, capsys):
    raw_path = tmp_path / "raw.json"
    out_path = tmp_path / "inventory.json"
    raw_path.write_text(
        json.dumps(
            [
                {"id": "1", "name": "jane", "source": "aws", "interactive_login": True},
                {
                    "id": "2",
                    "name": "lambda-exec",
                    "source": "aws",
                    "principal_kind": "iam_role",
                    "interactive_login": False,
                },
            ]
        )
    )

    exit_code = main(["classify", "--in", str(raw_path), "--out", str(out_path)])

    assert exit_code == 0
    data = json.loads(out_path.read_text())
    assert data["schema_version"] == "1.0"
    types = {r["id"]: r["type"] for r in data["records"]}
    assert types["1"] == "human"
    assert types["2"] == "nhi"

    captured = capsys.readouterr()
    assert "Classified 2 record(s)" in captured.out


def test_classify_missing_input_file_returns_nonzero(tmp_path, capsys):
    out_path = tmp_path / "inventory.json"
    exit_code = main(
        ["classify", "--in", str(tmp_path / "missing.json"), "--out", str(out_path)]
    )
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()
