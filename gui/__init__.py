"""ARGUS GUI: offline inventory browser and onboarding selection tool.

This package never performs network I/O. It only reads an inventory JSON
file produced by the ARGUS collectors and writes a selection JSON file
consumed by the CLI onboarder.
"""

__all__ = ["schema", "model", "selection"]
