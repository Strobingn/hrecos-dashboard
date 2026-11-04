"""ONNX export of the linear probe (softmax over classes).

The Perch backbone stays a separate ONNX or TFLite file. A Raspberry Pi can
run ``perch_v2_backbone.tflite`` and then this probe, either with ONNX Runtime
or with the NumPy implementation in :mod:`hrecos_ml.probe`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hrecos_ml.probe import LinearProbe


def fold_affine(probe: LinearProbe) -> tuple[np.ndarray, np.ndarray]:
    """Return W [C, D] and bias [C] such that logits = x @ W.T + bias."""
    weight = probe.coef / probe.scale.reshape(1, -1)
    bias = probe.intercept - (probe.mean / probe.scale) @ probe.coef.T
    return weight.astype(np.float32), bias.astype(np.float32)


def export_probe_onnx(probe: LinearProbe, path: str | Path) -> Path:
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    weight, bias = fold_affine(probe)
    n_class, n_feat = weight.shape
    w_init = numpy_helper.from_array(weight, name="weight")
    b_init = numpy_helper.from_array(bias, name="bias")
    inputs = [helper.make_tensor_value_info("features", TensorProto.FLOAT, ["batch", n_feat])]
    outputs = [helper.make_tensor_value_info("probabilities", TensorProto.FLOAT, ["batch", n_class])]
    gemm = helper.make_node(
        "Gemm",
        inputs=["features", "weight", "bias"],
        outputs=["logits"],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=1,
    )
    softmax = helper.make_node("Softmax", inputs=["logits"], outputs=["probabilities"], axis=1)
    graph = helper.make_graph([gemm, softmax], "hrecos_fish_probe", inputs, outputs, [w_init, b_init])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, str(path))
    return path


def onnx_predict_proba(onnx_path: str | Path, features: np.ndarray) -> np.ndarray:
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    x = np.asarray(features, dtype=np.float32)
    if x.ndim == 1:
        x = x.reshape(1, -1)
    return session.run(["probabilities"], {"features": x})[0]
