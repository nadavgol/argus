import pytest

from nhi_engine import taxonomy
from nhi_engine.classifier import TYPE_HUMAN, TYPE_NHI, classify, classify_all
from nhi_engine.schema import RawIdentityRecord


def make(**kwargs):
    defaults = {"id": "1", "name": "x", "source": "aws"}
    defaults.update(kwargs)
    return RawIdentityRecord(**defaults)


def test_interactive_login_is_human():
    result = classify(make(interactive_login=True))
    assert result.type == TYPE_HUMAN
    assert "Interactive login" in result.classification_reason


def test_interactive_login_with_mfa_noted_in_reason():
    result = classify(make(interactive_login=True, mfa_enabled=True))
    assert "MFA enabled" in result.classification_reason


def test_interactive_login_without_mfa_noted_in_reason():
    result = classify(make(interactive_login=True, mfa_enabled=False))
    assert "without MFA" in result.classification_reason


@pytest.mark.parametrize(
    "kwarg",
    [
        {"is_break_glass": True},
        {"is_shared_admin": True},
    ],
)
def test_break_glass_and_shared_admin_are_human(kwarg):
    result = classify(make(interactive_login=False, **kwarg))
    assert result.type == TYPE_HUMAN
    assert "human emergency" in result.classification_reason.lower() or (
        "shared" in result.classification_reason.lower()
    )


def test_break_glass_overrides_programmatic_signal():
    result = classify(
        make(interactive_login=False, credential_type="access_key", is_break_glass=True)
    )
    assert result.type == TYPE_HUMAN


@pytest.mark.parametrize(
    "principal_kind,expected_category",
    [
        ("iam_role", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("iam_user", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("instance_profile", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("service_principal", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("managed_identity", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("root_account", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("service_account", taxonomy.WORKLOAD_IDENTITY),
        ("pod_identity", taxonomy.WORKLOAD_IDENTITY),
        ("api_key", taxonomy.APPLICATION_CREDENTIAL),
        ("oauth_client", taxonomy.APPLICATION_CREDENTIAL),
        ("machine_account", taxonomy.MACHINE_ACCOUNT),
        ("gmsa", taxonomy.MACHINE_ACCOUNT),
        ("ad_service_account", taxonomy.MACHINE_ACCOUNT),
        ("spn_account", taxonomy.MACHINE_ACCOUNT),
        ("cert", taxonomy.CERTIFICATE),
        ("certificate", taxonomy.CERTIFICATE),
        ("mcp_server", taxonomy.AGENTIC_AI_IDENTITY),
        ("agent_identity", taxonomy.AGENTIC_AI_IDENTITY),
    ],
)
def test_principal_kind_maps_to_expected_category(principal_kind, expected_category):
    result = classify(make(interactive_login=False, principal_kind=principal_kind))
    assert result.type == TYPE_NHI
    assert expected_category in result.classification_reason
    assert result.subclass == principal_kind


@pytest.mark.parametrize(
    "credential_type,expected_category",
    [
        ("access_key", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("client_secret", taxonomy.CLOUD_IAM_PRINCIPAL),
        ("kerberos_keytab", taxonomy.MACHINE_ACCOUNT),
        ("service_account_token", taxonomy.WORKLOAD_IDENTITY),
        ("api_key", taxonomy.APPLICATION_CREDENTIAL),
        ("mcp_credential", taxonomy.AGENTIC_AI_IDENTITY),
    ],
)
def test_credential_type_maps_to_expected_category(credential_type, expected_category):
    result = classify(make(interactive_login=False, credential_type=credential_type))
    assert result.type == TYPE_NHI
    assert expected_category in result.classification_reason


def test_kubernetes_source_falls_back_to_workload_identity():
    result = classify(make(interactive_login=False, source="kubernetes"))
    assert result.type == TYPE_NHI
    assert taxonomy.WORKLOAD_IDENTITY in result.classification_reason


def test_no_signal_at_all_is_unclassified_nhi_not_human():
    result = classify(make())
    assert result.type == TYPE_NHI
    assert result.subclass == taxonomy.UNCLASSIFIED
    assert "manual review" in result.classification_reason.lower()


def test_unrecognized_principal_kind_and_source_is_unclassified_but_still_nhi():
    result = classify(
        make(interactive_login=False, source="generic", principal_kind="some_new_kind")
    )
    assert result.type == TYPE_NHI
    assert result.subclass == "some_new_kind"
    assert "could not map" in result.classification_reason.lower()


def test_unrecognized_principal_kind_falls_back_to_source_category():
    result = classify(make(interactive_login=False, principal_kind="some_new_kind"))
    assert result.type == TYPE_NHI
    assert taxonomy.CLOUD_IAM_PRINCIPAL in result.classification_reason


def test_explicit_non_interactive_with_no_other_signal_is_nhi():
    result = classify(make(interactive_login=False))
    assert result.type == TYPE_NHI


def test_classify_all_preserves_order_and_count():
    records = [make(id=str(i), interactive_login=(i % 2 == 0)) for i in range(5)]
    results = classify_all(records)
    assert len(results) == 5
    assert [r.type for r in results] == [
        TYPE_HUMAN if i % 2 == 0 else TYPE_NHI for i in range(5)
    ]
