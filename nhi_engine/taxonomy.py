"""NHI taxonomy: the fixed set of non-human identity categories.

Source of truth: issue #2 ("NHI Taxonomy and Discovery Surfaces"). That
issue is explicit that these six categories are fixed - "do not invent
alternatives" - so this module is intentionally a closed enum, not an
extensible registry.

Each category also carries the raw-signal `principal_kind` values that
map to it (see classifier.py), mirroring the "primary discovery surface"
column of the taxonomy table.
"""

from __future__ import annotations

from dataclasses import dataclass

CLOUD_IAM_PRINCIPAL = "cloud_iam_principal"
WORKLOAD_IDENTITY = "workload_identity"
APPLICATION_CREDENTIAL = "application_credential"
MACHINE_ACCOUNT = "machine_account"
CERTIFICATE = "certificate"
AGENTIC_AI_IDENTITY = "agentic_ai_identity"

# Not part of the taxonomy itself - used when a raw record carries
# insufficient signal to place it in one of the six categories above.
# Kept distinct so callers can filter these out for manual review rather
# than silently trusting a guess.
UNCLASSIFIED = "unclassified"

NHI_CATEGORIES = (
    CLOUD_IAM_PRINCIPAL,
    WORKLOAD_IDENTITY,
    APPLICATION_CREDENTIAL,
    MACHINE_ACCOUNT,
    CERTIFICATE,
    AGENTIC_AI_IDENTITY,
)


@dataclass(frozen=True)
class CategoryRule:
    category: str
    principal_kinds: frozenset[str]
    sources: frozenset[str]
    credential_types: frozenset[str]


# Ordered: first matching rule wins. See classifier.categorize_nhi().
CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        category=AGENTIC_AI_IDENTITY,
        principal_kinds=frozenset({"mcp_server", "agent_identity", "agentic_ai"}),
        sources=frozenset(),
        credential_types=frozenset({"mcp_credential", "agent_api_key"}),
    ),
    CategoryRule(
        category=CERTIFICATE,
        principal_kinds=frozenset({"cert", "certificate", "mtls_client_cert"}),
        sources=frozenset(),
        credential_types=frozenset({"certificate", "mtls_cert"}),
    ),
    CategoryRule(
        category=WORKLOAD_IDENTITY,
        principal_kinds=frozenset(
            {"service_account", "pod_identity", "workload_identity"}
        ),
        sources=frozenset({"kubernetes", "k8s"}),
        credential_types=frozenset({"service_account_token", "oidc_bound_token"}),
    ),
    CategoryRule(
        category=MACHINE_ACCOUNT,
        principal_kinds=frozenset(
            {"machine_account", "gmsa", "ad_service_account", "spn_account"}
        ),
        sources=frozenset({"active_directory", "ad"}),
        credential_types=frozenset({"kerberos_keytab", "ntlm_hash"}),
    ),
    CategoryRule(
        category=CLOUD_IAM_PRINCIPAL,
        principal_kinds=frozenset(
            {
                "iam_user",
                "iam_role",
                "instance_profile",
                "service_principal",
                "managed_identity",
                "root_account",
            }
        ),
        sources=frozenset({"aws", "azure", "entra", "gcp"}),
        credential_types=frozenset({"access_key", "client_secret"}),
    ),
    CategoryRule(
        category=APPLICATION_CREDENTIAL,
        principal_kinds=frozenset({"api_key", "oauth_client"}),
        sources=frozenset(),
        credential_types=frozenset({"api_key", "oauth_client_secret", "oauth_token"}),
    ),
)
