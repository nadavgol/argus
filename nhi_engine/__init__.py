"""ARGUS NHI engine: classifies identity records as human or non-human (NHI).

This package implements the Classifier layer of the ARGUS discovery
pipeline (see epic #11): it consumes raw, source-specific identity signals
and produces classified records compatible with the shared inventory
schema (schema_version "1.0") used by downstream tooling such as the GUI.
"""
