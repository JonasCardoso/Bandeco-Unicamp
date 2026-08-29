"""Fachada compatível para o pipeline nutricional."""

import sys

from nutrition import pipeline

sys.modules[__name__] = pipeline
