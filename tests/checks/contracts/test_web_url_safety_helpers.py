from __future__ import annotations

from loopora.web_url_utils import safe_attachment_filename, safe_local_return_path, with_query_params


def test_web_url_helpers_keep_redirects_and_filenames_local() -> None:
    assert safe_local_return_path("/bundles/bundle-1?tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("/bundles/bundle-1?token=secret&tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("https://example.test/bundles/1") is None
    assert safe_local_return_path("//example.test/bundles/1") is None
    assert safe_local_return_path("bundles/1") is None
    assert safe_local_return_path("/bundles\\example.test") is None
    assert safe_local_return_path("/bundles/1\r\nLocation: https://example.test") is None
    assert with_query_params("/bundles/bundle-1?tab=roles#surface", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow#surface"
    )
    assert with_query_params("/bundles/bundle-1?token=secret&tab=roles", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow"
    )
    assert safe_attachment_filename('Bad/Name" \r\n injected.yml') == "Bad-Name-injected.yml"
