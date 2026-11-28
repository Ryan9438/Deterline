"""样例定义闸门与引擎同源合同（16 号计划包 04）。

闸门 = samples/c1-cjk/defn_gate.py（进程内 importlib 载入，非 subprocess），
单一来源 = deterline.storyline._read_definition。本测试钉住：
1) 两个在册样例定义的闸门输出 == 引擎解析值；
2) 代表性分岔向量（重复键/字段大小写/引号布尔/非法 patch_id/行尾注释）
   与引擎裁决一致（同一错误类、指向字段）。
"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "samples" / "c1-cjk"
sys.path.insert(0, str(REPO / "scripts"))

from deterline.storyline import _read_definition  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "c1_defn_gate", SAMPLE / "defn_gate.py")
GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(GATE)


def _gate(path: Path):
    """跑闸门 main → (rc, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = GATE.main([str(path)])
    return rc, out.getvalue(), err.getvalue()


def _engine(doc_text: str):
    return _read_definition(doc_text)


class TestSampleDefnGateContract(unittest.TestCase):

    def _variant(self, name: str, text: str) -> Path:
        """临时目录中的定义变体。"""
        td = tempfile.mkdtemp(prefix="c1_gate_")
        p = Path(td) / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_ascii_sample_matches_engine(self):
        text = (SAMPLE / "defn_ascii.yaml").read_text(encoding="utf-8")
        doc = _engine(text)
        rc, out, _ = _gate(SAMPLE / "defn_ascii.yaml")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out),
                         {"patch_id": doc["patch_id"],
                          "cjk": bool(doc.get("cjk", False))})
        self.assertEqual(json.loads(out)["patch_id"], "det_c1_ascii")
        self.assertIs(json.loads(out)["cjk"], False)

    def test_cjk_sample_matches_engine(self):
        text = (SAMPLE / "defn_cjk.yaml").read_text(encoding="utf-8")
        doc = _engine(text)
        rc, out, _ = _gate(SAMPLE / "defn_cjk.yaml")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out),
                         {"patch_id": doc["patch_id"],
                          "cjk": bool(doc.get("cjk", False))})
        self.assertEqual(json.loads(out)["patch_id"], "det_c1_cjk")
        self.assertIs(json.loads(out)["cjk"], True)

    def test_duplicate_key_rejected_like_engine(self):
        text = (SAMPLE / "defn_ascii.yaml").read_text(encoding="utf-8")
        dup = text + "\npatch_id: det_other\n"
        try:
            _engine(dup)
            self.fail("引擎应拒绝重复键")
        except Exception as exc:
            engine_msg = str(exc)
        rc, _, err = _gate(self._variant("dup.yaml", dup))
        self.assertEqual(rc, 1)
        self.assertIn("重复键", engine_msg)
        self.assertIn("重复键", err)

    def test_field_case_rejected_like_engine(self):
        text = (SAMPLE / "defn_ascii.yaml").read_text(encoding="utf-8")
        variant = text.replace("patch_id:", "Patch_ID:", 1)
        try:
            _engine(variant)
            self.fail("引擎应拒绝大小写漂移键")
        except Exception as exc:
            engine_msg = str(exc)
        rc, _, err = _gate(self._variant("case.yaml", variant))
        self.assertEqual(rc, 1)
        self.assertIn("未知字段", engine_msg)
        self.assertIn("未知字段", err)

    def test_quoted_bool_rejected_like_engine(self):
        text = (SAMPLE / "defn_cjk.yaml").read_text(encoding="utf-8")
        variant = text.replace("cjk: true", 'cjk: "true"', 1)
        try:
            _engine(variant)
            self.fail("引擎应拒绝引号布尔")
        except Exception as exc:
            engine_msg = str(exc)
        rc, _, err = _gate(self._variant("quoted.yaml", variant))
        self.assertEqual(rc, 1)
        self.assertIn("cjk 必须是布尔", engine_msg)
        self.assertIn("cjk 必须是布尔", err)

    def test_bad_patch_id_rejected_like_engine(self):
        text = (SAMPLE / "defn_ascii.yaml").read_text(encoding="utf-8")
        variant = text.replace("patch_id: det_c1_ascii", "patch_id: Det-X", 1)
        try:
            _engine(variant)
            self.fail("引擎应拒绝非法 patch_id")
        except Exception as exc:
            engine_msg = str(exc)
        rc, _, err = _gate(self._variant("badid.yaml", variant))
        self.assertEqual(rc, 1)
        self.assertIn("patch_id 须匹配", engine_msg)
        self.assertIn("patch_id 须匹配", err)

    def test_trailing_comment_accepted_like_engine(self):
        text = (SAMPLE / "defn_cjk.yaml").read_text(encoding="utf-8")
        variant = text.replace("cjk: true", "cjk: true # 中文组合", 1)
        doc = _engine(variant)
        self.assertIs(doc.get("cjk"), True)
        rc, out, _ = _gate(self._variant("comment.yaml", variant))
        self.assertEqual(rc, 0)
        self.assertIs(json.loads(out)["cjk"], True)

    def test_missing_file_clean_error(self):
        rc, _, err = _gate(Path(tempfile.mkdtemp(prefix="c1_gate_")) / "nope.yaml")
        self.assertEqual(rc, 1)
        self.assertIn("定义读取失败", err)
