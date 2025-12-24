"""
Unit tests for the core.utils module.
Tests utility functions for file operations, command execution, and binary analysis.
"""

import base64
import json
import tempfile
from pathlib import Path

import pytest

from core.utils import (
    ensure_directory,
    tool_exists,
    get_timestamp,
    detect_binary_format,
    compute_entropy,
    get_file_size,
    base64_to_file,
    read_json,
    write_json,
    write_text,
    create_temp_directory,
    get_platform_triple,
    merge_flags,
    normalize_flags_and_passes,
    write_html,
    current_platform,
    is_windows_platform,
    make_executable,
    create_logger,
    read_text,
)
from core.exceptions import ObfuscationError


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_creates_single_directory(self, tmp_dir: Path):
        """Test creating a single directory."""
        new_dir = tmp_dir / "new_directory"
        ensure_directory(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_creates_nested_directories(self, tmp_dir: Path):
        """Test creating nested directories."""
        nested_dir = tmp_dir / "level1" / "level2" / "level3"
        ensure_directory(nested_dir)
        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_existing_directory_no_error(self, tmp_dir: Path):
        """Test that existing directory doesn't raise an error."""
        ensure_directory(tmp_dir)
        ensure_directory(tmp_dir)  # Should not raise


class TestToolExists:
    """Tests for tool_exists function."""

    def test_existing_tool(self):
        """Test with a tool that should exist on most systems."""
        # 'python' or 'python3' should exist since we're running Python
        assert tool_exists("python") or tool_exists("python3")

    def test_nonexistent_tool(self):
        """Test with a tool that definitely doesn't exist."""
        assert tool_exists("definitely_nonexistent_tool_xyz123") is False


class TestGetTimestamp:
    """Tests for get_timestamp function."""

    def test_returns_iso_format(self):
        """Test that timestamp is in ISO format with Z suffix."""
        timestamp = get_timestamp()
        assert timestamp.endswith("Z")
        # Should be parseable as ISO format
        assert "T" in timestamp

    def test_returns_string(self):
        """Test that timestamp returns a string."""
        assert isinstance(get_timestamp(), str)


class TestDetectBinaryFormat:
    """Tests for detect_binary_format function."""

    def test_elf_binary(self, sample_binary: Path):
        """Test detection of ELF binary format."""
        assert detect_binary_format(sample_binary) == "ELF"

    def test_pe_binary(self, sample_pe_binary: Path):
        """Test detection of PE binary format."""
        assert detect_binary_format(sample_pe_binary) == "PE"

    def test_unknown_format(self, tmp_dir: Path):
        """Test detection of unknown binary format."""
        unknown = tmp_dir / "unknown"
        unknown.write_bytes(b"UNKN" + b"\x00" * 60)
        assert detect_binary_format(unknown) == "unknown"

    def test_nonexistent_file(self, tmp_dir: Path):
        """Test with nonexistent file."""
        nonexistent = tmp_dir / "nonexistent"
        assert detect_binary_format(nonexistent) == "unknown"


class TestComputeEntropy:
    """Tests for compute_entropy function."""

    def test_empty_data(self):
        """Test entropy of empty data is 0."""
        assert compute_entropy(b"") == 0.0

    def test_single_byte_repeated(self):
        """Test entropy of repeated single byte is 0."""
        assert compute_entropy(b"\x00" * 100) == 0.0
        assert compute_entropy(b"AAAA") == 0.0

    def test_random_data_high_entropy(self):
        """Test that random-like data has higher entropy."""
        # All 256 possible byte values equally distributed would have max entropy
        all_bytes = bytes(range(256))
        entropy = compute_entropy(all_bytes)
        assert entropy > 7.0  # Close to maximum of 8.0

    def test_simple_pattern(self):
        """Test entropy of simple pattern."""
        # Alternating bytes
        pattern = b"\x00\xFF" * 50
        entropy = compute_entropy(pattern)
        assert 0 < entropy < 8.0


class TestGetFileSize:
    """Tests for get_file_size function."""

    def test_existing_file(self, sample_binary: Path):
        """Test getting size of existing file."""
        size = get_file_size(sample_binary)
        assert size > 0

    def test_nonexistent_file(self, tmp_dir: Path):
        """Test getting size of nonexistent file returns 0."""
        nonexistent = tmp_dir / "nonexistent"
        assert get_file_size(nonexistent) == 0


class TestBase64ToFile:
    """Tests for base64_to_file function."""

    def test_decode_and_write(self, tmp_dir: Path):
        """Test decoding base64 content and writing to file."""
        original = b"Hello, World!"
        encoded = base64.b64encode(original).decode("ascii")
        dest = tmp_dir / "decoded.txt"

        base64_to_file(encoded, dest)

        assert dest.exists()
        assert dest.read_bytes() == original


class TestJsonOperations:
    """Tests for read_json and write_json functions."""

    def test_write_and_read_json(self, tmp_dir: Path):
        """Test writing and reading JSON data."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_file = tmp_dir / "test.json"

        write_json(json_file, data)
        result = read_json(json_file)

        assert result == data

    def test_write_json_creates_directories(self, tmp_dir: Path):
        """Test that write_json creates parent directories."""
        json_file = tmp_dir / "nested" / "dir" / "test.json"
        data = {"test": True}

        write_json(json_file, data)

        assert json_file.exists()


class TestWriteText:
    """Tests for write_text function."""

    def test_write_text_file(self, tmp_dir: Path):
        """Test writing text content to file."""
        text_file = tmp_dir / "test.txt"
        content = "Hello, World!\nLine 2"

        write_text(text_file, content)

        assert text_file.exists()
        assert text_file.read_text(encoding="utf-8") == content

    def test_write_text_creates_directories(self, tmp_dir: Path):
        """Test that write_text creates parent directories."""
        text_file = tmp_dir / "nested" / "test.txt"

        write_text(text_file, "content")

        assert text_file.exists()


class TestCreateTempDirectory:
    """Tests for create_temp_directory function."""

    def test_creates_temp_directory(self):
        """Test creating temporary directory."""
        with create_temp_directory("test-") as tmpdir:
            path = Path(tmpdir)
            assert path.exists()
            assert path.is_dir()
            assert "test-" in path.name

    def test_cleanup_on_exit(self):
        """Test that temp directory is cleaned up on context exit."""
        with create_temp_directory("test-") as tmpdir:
            path = Path(tmpdir)
            test_file = path / "test.txt"
            test_file.write_text("test")

        # After context exit, directory should be cleaned up
        assert not path.exists()


class TestGetPlatformTriple:
    """Tests for get_platform_triple function."""

    def test_linux_triple(self):
        """Test platform triple for Linux."""
        assert get_platform_triple("linux") == "x86_64-pc-linux-gnu"

    def test_windows_triple(self):
        """Test platform triple for Windows."""
        assert get_platform_triple("windows") == "x86_64-pc-windows-msvc"


class TestMergeFlags:
    """Tests for merge_flags function."""

    def test_merge_empty_extra(self):
        """Test merging with no extra flags."""
        base = ["-O2", "-g"]
        result = merge_flags(base)
        assert result == ["-O2", "-g"]

    def test_merge_unique_flags(self):
        """Test merging unique flags."""
        base = ["-O2", "-g"]
        extra = ["-Wall", "-Werror"]
        result = merge_flags(base, extra)
        assert result == ["-O2", "-g", "-Wall", "-Werror"]

    def test_no_duplicate_flags(self):
        """Test that duplicate flags are not added."""
        base = ["-O2", "-g"]
        extra = ["-O2", "-Wall"]
        result = merge_flags(base, extra)
        assert result == ["-O2", "-g", "-Wall"]

    def test_allow_duplicate_mllvm(self):
        """Test that -mllvm flags can be duplicated."""
        base = ["-mllvm", "-fla"]
        extra = ["-mllvm", "-sub"]
        result = merge_flags(base, extra)
        assert result.count("-mllvm") == 2


class TestNormalizeFlagsAndPasses:
    """Tests for normalize_flags_and_passes function."""

    def test_empty_flags(self):
        """Test with empty flags list."""
        flags, passes = normalize_flags_and_passes([])
        assert flags == []
        assert all(v is False for v in passes.values())

    def test_regular_compiler_flags(self):
        """Test that regular compiler flags are preserved."""
        flags, passes = normalize_flags_and_passes(["-O2", "-g", "-Wall"])
        assert flags == ["-O2", "-g", "-Wall"]
        assert all(v is False for v in passes.values())

    def test_detect_flattening_pass(self):
        """Test detecting flattening pass."""
        flags, passes = normalize_flags_and_passes(["-fla"])
        assert "flattening" in passes
        assert passes["flattening"] is True
        assert "-fla" not in flags

    def test_detect_substitution_pass(self):
        """Test detecting substitution pass."""
        flags, passes = normalize_flags_and_passes(["-sub"])
        assert passes["substitution"] is True

    def test_detect_boguscf_pass(self):
        """Test detecting bogus control flow pass."""
        flags, passes = normalize_flags_and_passes(["-bcf"])
        assert passes["boguscf"] is True

    def test_detect_split_pass(self):
        """Test detecting split pass."""
        flags, passes = normalize_flags_and_passes(["-split"])
        assert passes["split"] is True

    def test_mllvm_pass_pattern(self):
        """Test -mllvm <pass> pattern detection."""
        flags, passes = normalize_flags_and_passes(["-mllvm", "-fla"])
        assert passes["flattening"] is True
        assert "-mllvm" not in flags
        assert "-fla" not in flags

    def test_mixed_flags_and_passes(self):
        """Test mixed compiler flags and pass flags."""
        input_flags = ["-O2", "-fla", "-g", "-mllvm", "-sub", "-Wall"]
        flags, passes = normalize_flags_and_passes(input_flags)
        assert "-O2" in flags
        assert "-g" in flags
        assert "-Wall" in flags
        assert passes["flattening"] is True
        assert passes["substitution"] is True


class TestWriteHtml:
    """Tests for write_html function."""

    def test_write_html_file(self, tmp_dir: Path):
        """Test writing HTML content to file."""
        html_file = tmp_dir / "test.html"
        content = "<html><body>Test</body></html>"

        write_html(html_file, content)

        assert html_file.exists()
        assert html_file.read_text(encoding="utf-8") == content


class TestCurrentPlatform:
    """Tests for current_platform function."""

    def test_returns_lowercase_string(self):
        """Test that current_platform returns lowercase string."""
        platform = current_platform()
        assert isinstance(platform, str)
        assert platform == platform.lower()


class TestIsWindowsPlatform:
    """Tests for is_windows_platform function."""

    def test_returns_boolean(self):
        """Test that function returns boolean."""
        result = is_windows_platform()
        assert isinstance(result, bool)


class TestMakeExecutable:
    """Tests for make_executable function."""

    def test_makes_file_executable(self, tmp_dir: Path):
        """Test making a file executable."""
        script = tmp_dir / "script.sh"
        script.write_text("#!/bin/bash\necho hello")

        # Initially may not be executable
        make_executable(script)

        # Check executable bit is set
        mode = script.stat().st_mode
        assert mode & 0o111  # At least one execute bit set


class TestCreateLogger:
    """Tests for create_logger function."""

    def test_creates_logger(self):
        """Test creating a logger."""
        import logging
        logger = create_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_has_handler(self):
        """Test that created logger has a handler."""
        logger = create_logger("test_logger_handler")
        assert len(logger.handlers) > 0


class TestReadText:
    """Tests for read_text function."""

    def test_read_text_file(self, tmp_dir: Path):
        """Test reading text content from file."""
        text_file = tmp_dir / "test.txt"
        content = "Hello, World!\nLine 2"
        text_file.write_text(content, encoding="utf-8")

        result = read_text(text_file)

        assert result == content
