"""Scientifically controlled benchmark utilities for SkyGuard."""

from .fault_injector import FAULT_TYPES, InjectionConfig, inject_partition
from .splits import split_genuine_observations, verify_no_source_overlap

__all__ = ["FAULT_TYPES", "InjectionConfig", "inject_partition",
           "split_genuine_observations", "verify_no_source_overlap"]
