from nhi_engine import taxonomy


def test_six_fixed_categories():
    assert len(taxonomy.NHI_CATEGORIES) == 6
    assert set(taxonomy.NHI_CATEGORIES) == {
        taxonomy.CLOUD_IAM_PRINCIPAL,
        taxonomy.WORKLOAD_IDENTITY,
        taxonomy.APPLICATION_CREDENTIAL,
        taxonomy.MACHINE_ACCOUNT,
        taxonomy.CERTIFICATE,
        taxonomy.AGENTIC_AI_IDENTITY,
    }


def test_unclassified_is_not_a_taxonomy_category():
    assert taxonomy.UNCLASSIFIED not in taxonomy.NHI_CATEGORIES


def test_every_rule_maps_to_a_fixed_category():
    for rule in taxonomy.CATEGORY_RULES:
        assert rule.category in taxonomy.NHI_CATEGORIES
