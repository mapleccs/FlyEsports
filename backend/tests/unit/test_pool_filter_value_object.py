"""
Unit tests for pool filter value object.
"""

import pytest
from datetime import datetime, timedelta

from src.domain.value_objects.pool_filter import PoolFilter


class TestPoolFilter:
    """Test suite for pool filter value object."""

    def test_create_default_filter(self):
        """Test creation of default pool filter."""
        filter_obj = PoolFilter.create_default()

        assert filter_obj.region_id is None
        assert filter_obj.position is None
        assert filter_obj.min_rating is None
        assert filter_obj.max_rating is None
        assert filter_obj.page == 1
        assert filter_obj.page_size == 20
        assert filter_obj.sort_by == "rating"
        assert filter_obj.sort_order == "desc"

    def test_create_default_filter_with_region(self):
        """Test creation of default pool filter with specific region."""
        filter_obj = PoolFilter.create_default(region_id=123)

        assert filter_obj.region_id == 123
        assert filter_obj.position is None
        assert filter_obj.min_rating is None
        assert filter_obj.max_rating is None

    def test_create_filter_with_all_parameters(self):
        """Test creation of filter with all parameters."""
        now = datetime.utcnow()

        filter_obj = PoolFilter(
            region_id=456,
            position="MIDDLE",
            min_rating=1500.0,
            max_rating=2000.0,
            min_confidence=0.7,
            max_confidence=0.9,
            min_matches=50,
            max_matches=200,
            contract_status="free_agent",
            last_active_days=30,
            dimension_filters={"kda": 60.0, "damage": 70.0},
            search_query="player name",
            include_inactive=False,
            page=2,
            page_size=50,
            sort_by="confidence",
            sort_order="asc"
        )

        assert filter_obj.region_id == 456
        assert filter_obj.position == "MIDDLE"
        assert filter_obj.min_rating == 1500.0
        assert filter_obj.max_rating == 2000.0
        assert filter_obj.min_confidence == 0.7
        assert filter_obj.max_confidence == 0.9
        assert filter_obj.min_matches == 50
        assert filter_obj.max_matches == 200
        assert filter_obj.contract_status == "free_agent"
        assert filter_obj.last_active_days == 30
        assert filter_obj.dimension_filters == {"kda": 60.0, "damage": 70.0}
        assert filter_obj.search_query == "player name"
        assert filter_obj.include_inactive is False
        assert filter_obj.page == 2
        assert filter_obj.page_size == 50
        assert filter_obj.sort_by == "confidence"
        assert filter_obj.sort_order == "asc"

    def test_valid_positions(self):
        """Test validation of valid positions."""
        valid_positions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

        for position in valid_positions:
            filter_obj = PoolFilter(position=position)
            assert filter_obj.position == position

        # None should also be valid
        filter_obj = PoolFilter(position=None)
        assert filter_obj.position is None

    def test_invalid_position_validation(self):
        """Test validation of invalid position."""
        with pytest.raises(ValueError, match="Invalid position"):
            PoolFilter(position="INVALID")

    def test_rating_range_validation(self):
        """Test validation of rating range."""
        # Valid range
        filter_obj = PoolFilter(min_rating=1000.0, max_rating=2000.0)
        assert filter_obj.min_rating == 1000.0
        assert filter_obj.max_rating == 2000.0

        # Min > Max should raise error
        with pytest.raises(ValueError, match="min_rating cannot be greater than max_rating"):
            PoolFilter(min_rating=2000.0, max_rating=1000.0)

        # Negative ratings should raise error
        with pytest.raises(ValueError, match="Ratings cannot be negative"):
            PoolFilter(min_rating=-100.0)

        with pytest.raises(ValueError, match="Ratings cannot be negative"):
            PoolFilter(max_rating=-50.0)

    def test_confidence_range_validation(self):
        """Test validation of confidence range."""
        # Valid range
        filter_obj = PoolFilter(min_confidence=0.6, max_confidence=0.9)
        assert filter_obj.min_confidence == 0.6
        assert filter_obj.max_confidence == 0.9

        # Min > Max should raise error
        with pytest.raises(ValueError, match="min_confidence cannot be greater than max_confidence"):
            PoolFilter(min_confidence=0.9, max_confidence=0.6)

        # Out of bounds confidence should raise error
        with pytest.raises(ValueError, match="Confidence must be between 0.5 and 0.95"):
            PoolFilter(min_confidence=0.3)

        with pytest.raises(ValueError, match="Confidence must be between 0.5 and 0.95"):
            PoolFilter(max_confidence=1.1)

    def test_matches_range_validation(self):
        """Test validation of matches range."""
        # Valid range
        filter_obj = PoolFilter(min_matches=10, max_matches=100)
        assert filter_obj.min_matches == 10
        assert filter_obj.max_matches == 100

        # Min > Max should raise error
        with pytest.raises(ValueError, match="min_matches cannot be greater than max_matches"):
            PoolFilter(min_matches=100, max_matches=10)

        # Negative matches should raise error
        with pytest.raises(ValueError, match="Match counts cannot be negative"):
            PoolFilter(min_matches=-1)

        with pytest.raises(ValueError, match="Match counts cannot be negative"):
            PoolFilter(max_matches=-1)

    def test_contract_status_validation(self):
        """Test validation of contract status."""
        valid_statuses = ["free_agent", "contracted", "loan", "trial", "all"]

        for status in valid_statuses:
            filter_obj = PoolFilter(contract_status=status)
            assert filter_obj.contract_status == status

        # None should also be valid (no filter)
        filter_obj = PoolFilter(contract_status=None)
        assert filter_obj.contract_status is None

        # Invalid status should raise error
        with pytest.raises(ValueError, match="Invalid contract status"):
            PoolFilter(contract_status="invalid_status")

    def test_last_active_days_validation(self):
        """Test validation of last active days."""
        # Valid values
        filter_obj = PoolFilter(last_active_days=30)
        assert filter_obj.last_active_days == 30

        filter_obj = PoolFilter(last_active_days=1)
        assert filter_obj.last_active_days == 1

        # Zero and negative should raise error
        with pytest.raises(ValueError, match="last_active_days must be positive"):
            PoolFilter(last_active_days=0)

        with pytest.raises(ValueError, match="last_active_days must be positive"):
            PoolFilter(last_active_days=-5)

    def test_dimension_filters_validation(self):
        """Test validation of dimension filters."""
        # Valid dimension filters
        valid_filters = {
            "kda": 60.0,
            "damage": 70.0,
            "economy": 55.0,
            "vision": 65.0,
            "objective": 80.0,
            "teamfight": 75.0
        }

        filter_obj = PoolFilter(dimension_filters=valid_filters)
        assert filter_obj.dimension_filters == valid_filters

        # Invalid dimension should raise error
        with pytest.raises(ValueError, match="Invalid dimension"):
            PoolFilter(dimension_filters={"invalid_dimension": 50.0})

        # Out of bounds score should raise error
        with pytest.raises(ValueError, match="Dimension scores must be between 0.0 and 100.0"):
            PoolFilter(dimension_filters={"kda": -10.0})

        with pytest.raises(ValueError, match="Dimension scores must be between 0.0 and 100.0"):
            PoolFilter(dimension_filters={"kda": 110.0})

    def test_page_validation(self):
        """Test validation of page parameter."""
        # Valid page
        filter_obj = PoolFilter(page=5)
        assert filter_obj.page == 5

        # Zero and negative page should raise error
        with pytest.raises(ValueError, match="Page must be positive"):
            PoolFilter(page=0)

        with pytest.raises(ValueError, match="Page must be positive"):
            PoolFilter(page=-1)

    def test_page_size_validation(self):
        """Test validation of page size parameter."""
        # Valid page sizes
        filter_obj = PoolFilter(page_size=10)
        assert filter_obj.page_size == 10

        filter_obj = PoolFilter(page_size=100)
        assert filter_obj.page_size == 100

        # Zero and negative should raise error
        with pytest.raises(ValueError, match="Page size must be positive"):
            PoolFilter(page_size=0)

        with pytest.raises(ValueError, match="Page size must be positive"):
            PoolFilter(page_size=-5)

        # Too large page size should raise error
        with pytest.raises(ValueError, match="Page size cannot exceed 100"):
            PoolFilter(page_size=150)

    def test_sort_by_validation(self):
        """Test validation of sort_by parameter."""
        valid_sort_fields = [
            "rating", "confidence", "matches_played", "last_updated",
            "kda", "damage", "economy", "vision", "objective", "teamfight"
        ]

        for field in valid_sort_fields:
            filter_obj = PoolFilter(sort_by=field)
            assert filter_obj.sort_by == field

        # Invalid sort field should raise error
        with pytest.raises(ValueError, match="Invalid sort field"):
            PoolFilter(sort_by="invalid_field")

    def test_sort_order_validation(self):
        """Test validation of sort_order parameter."""
        # Valid sort orders
        filter_obj = PoolFilter(sort_order="asc")
        assert filter_obj.sort_order == "asc"

        filter_obj = PoolFilter(sort_order="desc")
        assert filter_obj.sort_order == "desc"

        # Invalid sort order should raise error
        with pytest.raises(ValueError, match="Sort order must be 'asc' or 'desc'"):
            PoolFilter(sort_order="invalid")

    def test_calculate_offset(self):
        """Test offset calculation for pagination."""
        # Page 1, size 20: offset = 0
        filter_obj = PoolFilter(page=1, page_size=20)
        assert filter_obj.calculate_offset() == 0

        # Page 3, size 25: offset = 50
        filter_obj = PoolFilter(page=3, page_size=25)
        assert filter_obj.calculate_offset() == 50

        # Page 5, size 10: offset = 40
        filter_obj = PoolFilter(page=5, page_size=10)
        assert filter_obj.calculate_offset() == 40

    def test_has_rating_filter(self):
        """Test rating filter detection."""
        # No rating filter
        filter_obj = PoolFilter()
        assert not filter_obj.has_rating_filter()

        # Only min rating
        filter_obj = PoolFilter(min_rating=1500.0)
        assert filter_obj.has_rating_filter()

        # Only max rating
        filter_obj = PoolFilter(max_rating=2000.0)
        assert filter_obj.has_rating_filter()

        # Both ratings
        filter_obj = PoolFilter(min_rating=1500.0, max_rating=2000.0)
        assert filter_obj.has_rating_filter()

    def test_has_confidence_filter(self):
        """Test confidence filter detection."""
        # No confidence filter
        filter_obj = PoolFilter()
        assert not filter_obj.has_confidence_filter()

        # Only min confidence
        filter_obj = PoolFilter(min_confidence=0.7)
        assert filter_obj.has_confidence_filter()

        # Only max confidence
        filter_obj = PoolFilter(max_confidence=0.9)
        assert filter_obj.has_confidence_filter()

        # Both confidence values
        filter_obj = PoolFilter(min_confidence=0.7, max_confidence=0.9)
        assert filter_obj.has_confidence_filter()

    def test_has_activity_filter(self):
        """Test activity filter detection."""
        # No activity filter
        filter_obj = PoolFilter()
        assert not filter_obj.has_activity_filter()

        # With last_active_days
        filter_obj = PoolFilter(last_active_days=30)
        assert filter_obj.has_activity_filter()

        # With include_inactive False
        filter_obj = PoolFilter(include_inactive=False)
        assert filter_obj.has_activity_filter()

        # Both activity filters
        filter_obj = PoolFilter(last_active_days=30, include_inactive=False)
        assert filter_obj.has_activity_filter()

    def test_get_dimension_filter(self):
        """Test getting specific dimension filter."""
        dimension_filters = {"kda": 70.0, "damage": 80.0}
        filter_obj = PoolFilter(dimension_filters=dimension_filters)

        # Existing dimension
        assert filter_obj.get_dimension_filter("kda") == 70.0
        assert filter_obj.get_dimension_filter("damage") == 80.0

        # Non-existing dimension
        assert filter_obj.get_dimension_filter("vision") is None

        # No dimension filters at all
        filter_obj = PoolFilter()
        assert filter_obj.get_dimension_filter("kda") is None

    def test_immutability(self):
        """Test that pool filter is immutable."""
        filter_obj = PoolFilter(region_id=123, position="TOP")

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            filter_obj.region_id = 456

        with pytest.raises(AttributeError):
            filter_obj.position = "MIDDLE"

    def test_equality(self):
        """Test equality comparison."""
        filter1 = PoolFilter(region_id=123, position="TOP", min_rating=1500.0)
        filter2 = PoolFilter(region_id=123, position="TOP", min_rating=1500.0)

        assert filter1 == filter2

        # Different values should not be equal
        filter3 = PoolFilter(region_id=456, position="TOP", min_rating=1500.0)
        assert filter1 != filter3

    def test_hash_consistency(self):
        """Test hash consistency for same values."""
        filter1 = PoolFilter(region_id=123, position="TOP", min_rating=1500.0)
        filter2 = PoolFilter(region_id=123, position="TOP", min_rating=1500.0)

        # Same values should have same hash
        assert hash(filter1) == hash(filter2)

        # Different values should have different hash (usually)
        filter3 = PoolFilter(region_id=456, position="TOP", min_rating=1500.0)
        assert hash(filter1) != hash(filter3)

    def test_string_representation(self):
        """Test string representation."""
        filter_obj = PoolFilter(
            region_id=123,
            position="MIDDLE",
            min_rating=1500.0,
            page=2,
            page_size=30
        )

        str_repr = str(filter_obj)
        assert "PoolFilter" in str_repr
        assert "region_id=123" in str_repr
        assert "MIDDLE" in str_repr

    def test_complex_filter_combination(self):
        """Test complex combination of filters."""
        filter_obj = PoolFilter(
            region_id=789,
            position="JUNGLE",
            min_rating=1800.0,
            max_rating=2200.0,
            min_confidence=0.8,
            contract_status="free_agent",
            last_active_days=14,
            dimension_filters={"objective": 75.0, "vision": 60.0},
            search_query="experienced jungler",
            page=3,
            page_size=15,
            sort_by="rating",
            sort_order="desc"
        )

        # All filters should be properly set
        assert filter_obj.region_id == 789
        assert filter_obj.position == "JUNGLE"
        assert filter_obj.has_rating_filter()
        assert filter_obj.has_confidence_filter()
        assert filter_obj.has_activity_filter()
        assert filter_obj.get_dimension_filter("objective") == 75.0
        assert filter_obj.search_query == "experienced jungler"
        assert filter_obj.calculate_offset() == 30  # (3-1) * 15