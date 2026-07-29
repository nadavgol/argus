"""The NHI classifier: human/nhi split plus NHI category, per issue #2.

Rule order (first match wins), per the taxonomy doc's classification
rules plus its named edge cases:

1. Break-glass / shared-admin accounts -> human. These are provisioned
   for human emergency or shared interactive use even though they are
   not tied to one named person, so they are treated as human (subject
   to their own audit controls) rather than NHI.
2. Explicit interactive/console login capability -> human.
3. Explicit programmatic-only signal (interactive_login is False, or a
   recognized non-interactive credential_type/principal_kind) -> nhi,
   categorized into one of the six taxonomy categories.
4. Anything else (no usable signal either way) -> nhi/unclassified,
   flagged for manual review rather than silently defaulting to human.
   A security tool that guesses "human" on missing data would under-count
   NHIs, which is the failure mode this whole engine exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass

from nhi_engine import taxonomy
from nhi_engine.schema import RawIdentityRecord

TYPE_HUMAN = "human"
TYPE_NHI = "nhi"


@dataclass(frozen=True)
class ClassificationResult:
    type: str
    subclass: str
    classification_reason: str


def categorize_nhi(record: RawIdentityRecord) -> tuple[str, str]:
    """Map a non-human record to one of the six fixed NHI categories.

    Returns (category, reason_fragment). Falls back to UNCLASSIFIED when
    no rule matches.
    """
    principal_kind = (record.principal_kind or "").lower()
    source = (record.source or "").lower()
    credential_type = (record.credential_type or "").lower()

    for rule in taxonomy.CATEGORY_RULES:
        if principal_kind and principal_kind in rule.principal_kinds:
            return rule.category, f"principal kind '{record.principal_kind}'"
        if credential_type and credential_type in rule.credential_types:
            return rule.category, f"credential type '{record.credential_type}'"

    for rule in taxonomy.CATEGORY_RULES:
        if source and source in rule.sources:
            return rule.category, f"source '{record.source}'"

    return taxonomy.UNCLASSIFIED, "no recognized principal kind, credential type, or source"


def classify(record: RawIdentityRecord) -> ClassificationResult:
    """Classify a single raw identity record."""
    if record.is_break_glass or record.is_shared_admin:
        kind = "break-glass" if record.is_break_glass else "shared-admin"
        subclass = record.principal_kind or "shared_account"
        return ClassificationResult(
            type=TYPE_HUMAN,
            subclass=subclass,
            classification_reason=(
                f"Flagged as a {kind} account: provisioned for human "
                f"emergency/shared interactive use despite non-personal "
                f"ownership."
            ),
        )

    if record.interactive_login is True:
        mfa_note = ""
        if record.mfa_enabled is True:
            mfa_note = " with MFA enabled"
        elif record.mfa_enabled is False:
            mfa_note = " without MFA"
        return ClassificationResult(
            type=TYPE_HUMAN,
            subclass=record.principal_kind or "interactive_account",
            classification_reason=f"Interactive login capability detected{mfa_note}.",
        )

    has_programmatic_signal = (
        record.interactive_login is False
        or bool(record.credential_type)
        or bool(record.principal_kind)
    )
    if has_programmatic_signal:
        category, reason_fragment = categorize_nhi(record)
        subclass = record.principal_kind or category
        if category == taxonomy.UNCLASSIFIED:
            return ClassificationResult(
                type=TYPE_NHI,
                subclass=subclass,
                classification_reason=(
                    f"No interactive login capability, but {reason_fragment}; "
                    f"could not map to a taxonomy category, flagged for "
                    f"manual review."
                ),
            )
        return ClassificationResult(
            type=TYPE_NHI,
            subclass=subclass,
            classification_reason=(
                f"No interactive login capability; classified as "
                f"'{category}' via {reason_fragment}."
            ),
        )

    return ClassificationResult(
        type=TYPE_NHI,
        subclass=taxonomy.UNCLASSIFIED,
        classification_reason=(
            "Insufficient signal to determine interactive-login capability "
            "or principal kind; flagged for manual review rather than "
            "assumed human."
        ),
    )


def classify_all(records: list[RawIdentityRecord]) -> list[ClassificationResult]:
    return [classify(r) for r in records]
