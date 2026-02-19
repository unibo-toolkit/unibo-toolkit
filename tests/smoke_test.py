#!/usr/bin/env python3
"""Smoke test to verify basic package functionality across Python versions."""

import sys
from datetime import datetime


def test_imports():
    """Test that all main package imports work."""
    print("Testing imports...")

    # Main package import
    import unibo_toolkit

    # Verify version exists
    assert hasattr(unibo_toolkit, "__version__")
    print(f"  ✓ Package version: {unibo_toolkit.__version__}")

    # Test all public imports
    from unibo_toolkit import (
        AccessType,
        Area,
        AreaInfo,
        Bachelor,
        BaseCourse,
        Campus,
        CourseScraper,
        CourseType,
        HTTPClient,
        Language,
        Master,
        SingleCycleMaster,
        setup_logging,
    )

    print("  ✓ All public imports successful")

    # Test exception imports
    from unibo_toolkit.exceptions import (
        CourseNotFoundError,
        InvalidAreaError,
        ScraperError,
        UniboToolkitError,
        UnsupportedLanguageError,
    )

    print("  ✓ Exception imports successful")

    # Test model imports
    from unibo_toolkit.models import Curriculum

    print("  ✓ Model imports successful")

    return True


def test_enums():
    """Test that enums are properly defined and accessible."""
    print("\nTesting enums...")

    from unibo_toolkit import AccessType, Area, Campus, CourseType, Language

    # Test Area enum (academic areas)
    assert hasattr(Area, "SCIENZE")
    assert hasattr(Area, "INGEGNERIA_ARCHITETTURA")
    assert Area.SCIENZE.area_id == 9
    print("  ✓ Area enum works")

    # Test Language enum
    assert hasattr(Language, "IT")
    assert hasattr(Language, "EN")
    assert hasattr(Language, "FR")
    print("  ✓ Language enum works")

    # Test CourseType enum
    assert hasattr(CourseType, "BACHELOR")
    assert hasattr(CourseType, "MASTER")
    assert hasattr(CourseType, "SINGLE_CYCLE_MASTER")
    print("  ✓ CourseType enum works")

    # Test Campus enum
    assert hasattr(Campus, "BOLOGNA")
    assert Campus.BOLOGNA.value == "bologna"
    print("  ✓ Campus enum works")

    # Test AccessType enum
    assert hasattr(AccessType, "OPEN")
    assert hasattr(AccessType, "LIMITED")
    print("  ✓ AccessType enum works")

    return True


def test_models():
    """Test that model classes can be instantiated."""
    print("\nTesting model creation...")

    from unibo_toolkit import (
        AccessType,
        Area,
        AreaInfo,
        Bachelor,
        Campus,
        CourseType,
        Language,
    )

    # Test AreaInfo creation
    area_info = AreaInfo(
        area=Area.SCIENZE,
        course_count=10,
        course_type=CourseType.BACHELOR,
    )
    assert area_info.area == Area.SCIENZE
    assert area_info.course_count == 10
    print("  ✓ AreaInfo model created")

    # Test Bachelor creation
    bachelor = Bachelor(
        course_id=12345,
        title="Test Course",
        course_class="L-31",
        campus=Campus.BOLOGNA,
        languages=[Language.EN],
        duration_years=3,
        access_type=AccessType.OPEN,
        year=2024,
        url="https://www.unibo.it/test",
    )
    assert bachelor.course_id == 12345
    assert bachelor.title == "Test Course"
    assert bachelor.get_course_type() == CourseType.BACHELOR
    print("  ✓ Bachelor model created")

    # Test that Bachelor inherits from BaseCourse
    from unibo_toolkit.models import BaseCourse

    assert isinstance(bachelor, BaseCourse)
    print("  ✓ Model inheritance works")

    return True


def test_curriculum():
    """Test Curriculum model."""
    print("\nTesting Curriculum model...")

    from unibo_toolkit.models import Curriculum

    # Test Curriculum creation
    curriculum = Curriculum(
        code="000-000",
        label="General Track",
        selected=True,
    )
    assert curriculum.code == "000-000"
    assert curriculum.label == "General Track"
    assert curriculum.selected is True
    print("  ✓ Curriculum model created")

    return True


def test_http_client():
    """Test HTTPClient can be instantiated."""
    print("\nTesting HTTPClient...")

    from unibo_toolkit import HTTPClient

    # Create client (but don't make actual requests)
    client = HTTPClient()
    assert client is not None
    print("  ✓ HTTPClient created")

    return True


def test_scrapers():
    """Test that scrapers can be imported and instantiated."""
    print("\nTesting scrapers...")

    from unibo_toolkit import CourseScraper

    # Test CourseScraper instantiation
    scraper = CourseScraper()
    assert scraper is not None
    print("  ✓ CourseScraper created")

    # Test other scrapers can be imported
    from unibo_toolkit.scrapers import SubjectsScraper, TimetableScraper

    print("  ✓ All scrapers imported")

    return True


def test_utilities():
    """Test utility modules."""
    print("\nTesting utilities...")

    # Test parsers
    from unibo_toolkit.utils import parsers, subjects_parser, timetable_parser

    print("  ✓ Parser utilities imported")

    # Test date utils
    from unibo_toolkit.utils import date_utils

    print("  ✓ Date utilities imported")

    # Test timetable filters
    from unibo_toolkit.utils import timetable_filters

    print("  ✓ Timetable filters imported")

    return True


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("UniBo Toolkit Smoke Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("=" * 60)

    tests = [
        test_imports,
        test_enums,
        test_models,
        test_curriculum,
        test_http_client,
        test_scrapers,
        test_utilities,
    ]

    failed = []

    for test in tests:
        try:
            if not test():
                failed.append(test.__name__)
        except Exception as e:
            print(f"  ✗ {test.__name__} failed: {e}")
            failed.append(test.__name__)

    print("\n" + "=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("SUCCESS: All smoke tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
