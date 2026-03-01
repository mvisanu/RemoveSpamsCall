"""Unit tests for legal letter generation."""

from privacytool.letters.generator import render_letter


def test_gdpr_letter_renders(sample_profile):
    text = render_letter(
        "gdpr",
        sample_profile,
        target_site="example.com",
        urls=["https://example.com/listing/123"],
    )
    assert "Article 17" in text
    assert "Jane Doe" in text
    assert "example.com" in text
    assert "https://example.com/listing/123" in text
    assert "LEGAL DISCLAIMER" in text


def test_ccpa_letter_renders(sample_profile):
    text = render_letter(
        "ccpa",
        sample_profile,
        target_site="databroker.com",
        urls=["https://databroker.com/record/456"],
    )
    assert "1798.105" in text
    assert "Jane Doe" in text
    assert "California" in text


def test_general_letter_renders(sample_profile):
    text = render_letter(
        "general",
        sample_profile,
        target_site="spamsite.net",
        urls=["https://spamsite.net/p/789"],
    )
    assert "Jane Doe" in text
    assert "spamsite.net" in text


def test_letter_save_txt(tmp_path, sample_profile):
    from privacytool.letters.generator import generate_letter
    results = generate_letter(
        "general",
        sample_profile,
        target_site="example.com",
        urls=["https://example.com/foo"],
        output_dir=tmp_path,
        formats=["txt"],
    )
    assert "txt" in results
    import pathlib
    assert pathlib.Path(results["txt"]).exists()
