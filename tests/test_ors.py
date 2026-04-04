from unittest.mock import MagicMock, patch
import pytest
import ors


def _geo_response(lon, lat):
    """Build a minimal ORS geocode response."""
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "features": [{"geometry": {"coordinates": [lon, lat]}, "properties": {"label": f"{lon},{lat}"}}]
    }
    return mock


def _directions_response(metres):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"routes": [{"summary": {"distance": metres}}]}
    return mock


def test_geocode_returns_coordinates():
    with patch("ors.requests.get", return_value=_geo_response(-122.41, 37.77)):
        lon, lat = ors.geocode("San Francisco, CA")
    assert lon == pytest.approx(-122.41)
    assert lat == pytest.approx(37.77)


def test_geocode_raises_on_empty_features():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"features": []}
    with patch("ors.requests.get", return_value=mock):
        with pytest.raises(ors.ORSError, match="No geocoding results"):
            ors.geocode("nowhere special")


def test_autocomplete_returns_formatted_list():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "features": [
            {"geometry": {"coordinates": [-122.41, 37.77]}, "properties": {"label": "San Francisco, CA"}},
            {"geometry": {"coordinates": [-118.24, 34.05]}, "properties": {"label": "Los Angeles, CA"}},
        ]
    }
    with patch("ors.requests.get", return_value=mock):
        results = ors.autocomplete("San")
    assert len(results) == 2
    assert results[0]["label"] == "San Francisco, CA"
    assert results[0]["lon"] == pytest.approx(-122.41)
    assert results[0]["lat"] == pytest.approx(37.77)


def _empty_ac_mock():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"features": []}
    return mock


def test_autocomplete_passes_explicit_focus():
    with patch("ors.requests.get", return_value=_empty_ac_mock()) as mock_get:
        ors.autocomplete("park", focus={"lon": -122.41, "lat": 37.77})
    call_params = mock_get.call_args[1]["params"]
    assert call_params["focus.point.lon"] == -122.41
    assert call_params["focus.point.lat"] == 37.77


def test_autocomplete_falls_back_to_sunnyvale():
    """When no focus is provided, should default to the Sunnyvale fallback coordinates."""
    with patch("ors.requests.get", return_value=_empty_ac_mock()) as mock_get:
        with patch.object(ors.config, "GEOCODE_FOCUS", None):
            ors.autocomplete("Main St")
    call_params = mock_get.call_args[1]["params"]
    assert call_params["focus.point.lon"] == pytest.approx(-122.04)
    assert call_params["focus.point.lat"] == pytest.approx(37.37)


def test_autocomplete_sends_layers_filter():
    with patch("ors.requests.get", return_value=_empty_ac_mock()) as mock_get:
        ors.autocomplete("park")
    call_params = mock_get.call_args[1]["params"]
    assert "layers" in call_params
    assert "address" in call_params["layers"]
    assert "venue" in call_params["layers"]


def test_autocomplete_restricts_to_north_america():
    with patch("ors.requests.get", return_value=_empty_ac_mock()) as mock_get:
        ors.autocomplete("park")
    call_params = mock_get.call_args[1]["params"]
    assert "boundary.country" in call_params
    assert "USA" in call_params["boundary.country"]


def test_driving_miles_converts_metres():
    # 1609.344 metres = 1.0 miles exactly
    with patch("ors.geocode", side_effect=[(-122.41, 37.77), (-118.24, 34.05)]):
        with patch("ors.requests.post", return_value=_directions_response(16093.44)):
            miles = ors.driving_miles("San Francisco", "Los Angeles")
    assert miles == pytest.approx(10.0, rel=1e-4)


def test_driving_miles_raises_on_bad_status():
    bad = MagicMock()
    bad.status_code = 429
    bad.text = "Rate limit exceeded"
    with patch("ors.geocode", side_effect=[(-122.0, 37.0), (-118.0, 34.0)]):
        with patch("ors.requests.post", return_value=bad):
            with pytest.raises(ors.ORSError, match="ORS directions failed"):
                ors.driving_miles("A", "B")
