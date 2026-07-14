from __future__ import annotations

import json
from pathlib import Path
import tarfile
from zipfile import BadZipFile, ZipFile

from loopora.package_source_provenance import SOURCE_PROVENANCE_FILENAME, normalized_source_provenance

_PROVENANCE_KEYS = {"schema_version", "revision", "tree_status"}


def package_source_provenance_errors(wheel_path: Path, sdist_path: Path) -> list[str]:
    wheel_payload, wheel_error = _wheel_provenance_payload(wheel_path)
    sdist_payload, sdist_error = _sdist_provenance_payload(sdist_path)
    errors = [message for message in (wheel_error, sdist_error) if message]
    wheel_provenance, wheel_validation_error = _validated_provenance(wheel_payload, artifact="wheel")
    sdist_provenance, sdist_validation_error = _validated_provenance(sdist_payload, artifact="sdist")
    errors.extend(message for message in (wheel_validation_error, sdist_validation_error) if message)
    if wheel_provenance and sdist_provenance and wheel_provenance != sdist_provenance:
        errors.append("wheel and sdist source provenance do not match")
    return errors


def _wheel_provenance_payload(wheel_path: Path) -> tuple[object, str]:
    member = f"loopora/{SOURCE_PROVENANCE_FILENAME}"
    try:
        with ZipFile(wheel_path) as wheel:
            if member not in wheel.namelist():
                return None, f"wheel missing source provenance: {member}"
            return json.loads(wheel.read(member).decode("utf-8")), ""
    except (BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"wheel source provenance is unreadable: {exc}"


def _sdist_provenance_payload(sdist_path: Path) -> tuple[object, str]:
    suffix = f"/src/loopora/{SOURCE_PROVENANCE_FILENAME}"
    try:
        with tarfile.open(sdist_path) as sdist:
            members = [member for member in sdist.getmembers() if member.name.endswith(suffix)]
            if len(members) != 1:
                return None, f"sdist expected one source provenance file, found {len(members)}"
            stream = sdist.extractfile(members[0])
            if stream is None:
                return None, "sdist source provenance is unreadable"
            return json.loads(stream.read().decode("utf-8")), ""
    except (tarfile.TarError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"sdist source provenance is unreadable: {exc}"


def _validated_provenance(payload: object, *, artifact: str) -> tuple[dict[str, str] | None, str]:
    if payload is None:
        return None, ""
    if not isinstance(payload, dict) or set(payload) != _PROVENANCE_KEYS:
        return None, f"{artifact} source provenance must contain only schema_version, revision, and tree_status"
    normalized = normalized_source_provenance(payload)
    if normalized is None:
        return None, f"{artifact} source provenance has an invalid revision or tree status"
    return normalized, ""
