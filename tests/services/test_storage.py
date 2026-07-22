from app.services.storage import supports_upload


def test_supported_extension_accepts_generic_browser_mime_type() -> None:
    assert supports_upload("notes.csv", "application/octet-stream")


def test_unsupported_extension_is_rejected_even_with_generic_mime_type() -> None:
    assert not supports_upload("unsafe.exe", "application/octet-stream")
