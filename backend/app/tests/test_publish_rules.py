"""Tests for the publish_rules classification service."""

from app.services.publish_rules import (
    TIER_AUTO,
    TIER_BLOCK,
    TIER_HOLD,
    classify_record,
    public_visibility_for_tier,
    review_status_for_tier,
    source_tier,
    is_publishable,
    check_publication_safety,
)

# ---------------------------------------------------------------------------
# source_tier lookup
# ---------------------------------------------------------------------------


def test_source_tier_auto_publish_safe_sources():
    for name in [
        "natural_earth",
        "geonames",
        "court_location_registry",
        "statistics_canada",
        "fbi_crime_data",
        "chicago_data_portal",
        "toronto_police",
        "saskatoon_police",
        "los_angeles_open_data",
    ]:
        assert source_tier(name) == TIER_AUTO, f"{name} should be TIER_AUTO"


def test_source_tier_hold_sources():
    for name in ["courtlistener", "gdelt", "news", "media_cloud", "court_opinion_rss"]:
        assert source_tier(name) == TIER_HOLD, f"{name} should be TIER_HOLD"


def test_source_tier_unknown_defaults_to_hold():
    assert source_tier("some_random_source") == TIER_HOLD


# ---------------------------------------------------------------------------
# classify_record — tier passthrough
# ---------------------------------------------------------------------------


def test_classify_auto_source_clean_record_returns_auto():
    record = {"precision_level": "city_centroid", "notes": None}
    assert classify_record("statistics_canada", record) == TIER_AUTO


def test_classify_hold_source_clean_record_returns_hold():
    record = {"precision_level": "city_centroid", "notes": None}
    assert classify_record("courtlistener", record) == TIER_HOLD


def test_classify_gdelt_source_always_hold():
    record = {"precision_level": "city_centroid", "notes": "Court ruling article."}
    assert classify_record("gdelt", record) == TIER_HOLD


# ---------------------------------------------------------------------------
# classify_record — block patterns
# ---------------------------------------------------------------------------


def test_classify_blocks_exact_address_in_notes():
    record = {
        "precision_level": "city_centroid",
        "notes": "Incident occurred at 123 Main Street.",
    }
    assert classify_record("chicago_data_portal", record) == TIER_BLOCK


def test_classify_blocks_causal_judge_language():
    record = {
        "precision_level": "city_centroid",
        "notes": "Judge Smith caused the crime wave.",
    }
    assert classify_record("statistics_canada", record) == TIER_BLOCK


def test_classify_blocks_social_media_text():
    record = {
        "precision_level": "city_centroid",
        "docket_text": "Based on a tweet by the defendant.",
    }
    assert classify_record("courtlistener", record) == TIER_BLOCK


def test_classify_blocks_defendant_name_in_docket_text():
    record = {
        "precision_level": "city_centroid",
        "docket_text": "Defendant John Smith sentenced.",
    }
    assert classify_record("courtlistener", record) == TIER_BLOCK


# ---------------------------------------------------------------------------
# classify_record — auto→hold bumps for person names / exact precision
# ---------------------------------------------------------------------------


def test_classify_auto_source_bumps_to_hold_with_judge_name():
    record = {"precision_level": "city_centroid", "judge_name": "Hon. Alice Doe"}
    assert classify_record("chicago_data_portal", record) == TIER_HOLD


def test_classify_auto_source_bumps_to_hold_with_exact_precision():
    record = {"precision_level": "exact_address", "notes": None}
    assert classify_record("fbi_crime_data", record) == TIER_HOLD


def test_classify_auto_source_bumps_to_hold_with_parties():
    record = {"precision_level": "city_centroid", "parties": [{"name": "Someone"}]}
    assert classify_record("statistics_canada", record) == TIER_HOLD


# ---------------------------------------------------------------------------
# review_status_for_tier / public_visibility_for_tier
# ---------------------------------------------------------------------------


def test_review_status_auto():
    assert review_status_for_tier(TIER_AUTO) == "official_police_open_data_report"


def test_review_status_hold():
    assert review_status_for_tier(TIER_HOLD) == "pending_review"


def test_public_visibility_auto():
    assert public_visibility_for_tier(TIER_AUTO) is True


def test_public_visibility_hold():
    assert public_visibility_for_tier(TIER_HOLD) is False


def test_public_visibility_block():
    assert public_visibility_for_tier(TIER_BLOCK) is False


# ---------------------------------------------------------------------------
# is_publishable — publication gate tests
# ---------------------------------------------------------------------------


def test_is_publishable_valid_record_passes():
    """A complete valid record should be publishable."""
    record = {
        "source_url": "https://example.com/court-record/123",
        "source_tier": "court_record",
        "precision_level": "city_centroid",
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is True
    assert reasons == []


def test_is_publishable_missing_source_url_blocked():
    """Missing source_url should block publication."""
    record = {
        "source_url": None,
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert "missing_source_url" in reasons


def test_is_publishable_empty_source_url_blocked():
    """Empty source_url string should block publication."""
    record = {
        "source_url": "   ",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert "missing_source_url" in reasons


def test_is_publishable_invalid_source_tier_blocked():
    """Invalid source_tier should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "random_blog",
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert any("invalid_source_tier" in r for r in reasons)


def test_is_publishable_private_address_precision_blocked():
    """Exact private address precision should block publication."""
    for bad_precision in ["exact_private_address", "exact_residence", "home_address"]:
        record = {
            "source_url": "https://example.com/record",
            "source_tier": "official_police_open_data",
            "precision_level": bad_precision,
            "review_status": "official_police_open_data_report",
            "public_visibility": True,
        }
        is_ok, reasons = is_publishable(record)
        assert is_ok is False, f"Should block precision: {bad_precision}"
        assert any("blocked_precision" in r for r in reasons)


def test_is_publishable_safe_precision_allowed():
    """General area precision should be allowed."""
    for good_precision in ["city_centroid", "neighbourhood", "general_area"]:
        record = {
            "source_url": "https://example.com/record",
            "source_tier": "official_police_open_data",
            "precision_level": good_precision,
            "review_status": "official_police_open_data_report",
            "public_visibility": True,
        }
        is_ok, reasons = is_publishable(record)
        assert is_ok is True, f"Should allow precision: {good_precision}"


def test_is_publishable_pending_review_blocked():
    """Pending review status should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "pending_review",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert any("unapproved_status" in r for r in reasons)


def test_is_publishable_rejected_status_blocked():
    """Rejected status should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "rejected",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert any("unapproved_status" in r for r in reasons)


def test_is_publishable_public_visibility_false_blocked():
    """False public_visibility should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": False,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert "public_visibility_false" in reasons


def test_is_publishable_unresolved_safety_flags_blocked():
    """Unresolved safety flags should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": True,
        "safety_flags": [
            {"type": "privacy_risk", "resolved": False},
            {"type": "data_quality", "resolved": True},
        ],
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert any("unresolved_safety_flags" in r for r in reasons)


def test_is_publishable_resolved_safety_flags_allowed():
    """Resolved safety flags should not block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": True,
        "safety_flags": [
            {"type": "privacy_risk", "resolved": True},
        ],
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is True


def test_is_publishable_unsupported_linkage_blocked():
    """Unsupported judge/crime linkage should block publication."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "public_visibility": True,
        "judge_crime_linkage_status": "inferred_unsupported",
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is False
    assert "unsupported_judge_crime_linkage" in reasons


def test_is_publishable_source_quality_fallback():
    """source_quality field should be used as fallback for source_tier."""
    record = {
        "source_url": "https://example.com/record",
        "source_quality": "court_record",  # Using source_quality instead of source_tier
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is True


def test_is_publishable_is_public_fallback():
    """is_public field should be used as fallback for public_visibility."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "review_status": "verified_court_record",
        "is_public": True,  # Using is_public instead of public_visibility
    }
    is_ok, reasons = is_publishable(record)
    assert is_ok is True


# ---------------------------------------------------------------------------
# check_publication_safety — detailed report tests
# ---------------------------------------------------------------------------


def test_check_publication_safety_returns_full_report():
    """check_publication_safety should return detailed safety report."""
    record = {
        "source_url": "https://example.com/record",
        "source_tier": "court_record",
        "precision_level": "city_centroid",
        "review_status": "verified_court_record",
        "public_visibility": True,
    }
    report = check_publication_safety(record)
    assert report["safe_to_publish"] is True
    assert report["can_be_public"] is True
    assert report["blocking_reasons"] == []
    assert report["checks"]["has_source_url"] is True
    assert report["checks"]["valid_source_tier"] is True
    assert report["checks"]["safe_precision"] is True
    assert report["checks"]["approved_status"] is True
    assert report["checks"]["public_visibility_enabled"] is True


def test_check_publication_safety_reports_blocking_reasons():
    """check_publication_safety should report all blocking reasons."""
    record = {
        "source_url": None,
        "source_tier": "invalid_tier",
        "precision_level": "exact_private_address",
        "review_status": "pending_review",
        "public_visibility": False,
    }
    report = check_publication_safety(record)
    assert report["safe_to_publish"] is False
    assert len(report["blocking_reasons"]) >= 4  # Multiple issues
    assert report["checks"]["has_source_url"] is False
    assert report["checks"]["valid_source_tier"] is False
    assert report["checks"]["safe_precision"] is False
    assert report["checks"]["approved_status"] is False
    assert report["checks"]["public_visibility_enabled"] is False
