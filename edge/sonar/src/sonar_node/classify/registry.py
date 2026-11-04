"""Build a classifier from config. A future frame model plugs in as 'ml'."""

from __future__ import annotations

import importlib
from typing import Any

from sonar_node.classify.base import SonarClassifier
from sonar_node.classify.rules import RulesClassifier


def load_entrypoint(entrypoint: str) -> SonarClassifier:
    """Load ``package.module:attribute``.

    The attribute may be a classifier instance, a zero-arg factory, or a class.
    The result must implement ``classify(track)``.
    """
    module_name, separator, attribute = entrypoint.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError(
            "classifier entrypoint must look like 'package.module:build_classifier'"
        )
    module = importlib.import_module(module_name)
    obj: Any = module
    for part in attribute.split("."):
        obj = getattr(obj, part)
    classifier = obj() if isinstance(obj, type) else obj() if callable(obj) else obj
    if not hasattr(classifier, "classify"):
        raise TypeError(f"{entrypoint} did not produce a classifier with classify()")
    return classifier


def build_classifier(name: str, entrypoint: str | None = None) -> SonarClassifier:
    if name in ("rules", "", None):
        return RulesClassifier()
    if name == "ml":
        if not entrypoint:
            raise ValueError(
                "classifier.name is 'ml' but classifier.entrypoint is empty"
            )
        return load_entrypoint(entrypoint)
    raise ValueError(
        f"unknown classifier '{name}'. Use 'rules', or 'ml' with an entrypoint."
    )
