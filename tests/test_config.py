"""
Unit tests for the core.config module.
Tests configuration dataclasses, enums, and configuration parsing.
"""

import pytest
from pathlib import Path

from core.config import (
    Platform,
    Architecture,
    MLIRFrontend,
    ObfuscationLevel,
    CryptoHashAlgorithm,
    CryptoHashConfiguration,
    PassConfiguration,
    IndirectCallConfiguration,
    UPXConfiguration,
    RemarksConfiguration,
    AntiDebugConfiguration,
    AdvancedConfiguration,
    OutputConfiguration,
    ObfuscationConfig,
    AnalyzeConfig,
    CompareConfig,
)


class TestPlatform:
    """Tests for Platform enum."""

    def test_platform_values(self):
        """Test all platform enum values exist."""
        assert Platform.LINUX.value == "linux"
        assert Platform.WINDOWS.value == "windows"
        assert Platform.MACOS.value == "macos"
        assert Platform.DARWIN.value == "darwin"
        assert Platform.ALL.value == "all"

    def test_platform_from_string_valid(self):
        """Test Platform.from_string with valid inputs."""
        assert Platform.from_string("linux") == Platform.LINUX
        assert Platform.from_string("LINUX") == Platform.LINUX
        assert Platform.from_string("windows") == Platform.WINDOWS
        assert Platform.from_string("macos") == Platform.MACOS
        # Darwin should map to macos
        assert Platform.from_string("darwin") == Platform.MACOS
        assert Platform.from_string("DARWIN") == Platform.MACOS

    def test_platform_from_string_invalid(self):
        """Test Platform.from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            Platform.from_string("invalid_platform")


class TestArchitecture:
    """Tests for Architecture enum."""

    def test_architecture_values(self):
        """Test all architecture enum values exist."""
        assert Architecture.X86_64.value == "x86_64"
        assert Architecture.ARM64.value == "arm64"
        assert Architecture.X86.value == "i686"

    def test_architecture_from_string_valid(self):
        """Test Architecture.from_string with valid inputs."""
        assert Architecture.from_string("x86_64") == Architecture.X86_64
        assert Architecture.from_string("amd64") == Architecture.X86_64
        assert Architecture.from_string("x64") == Architecture.X86_64
        assert Architecture.from_string("arm64") == Architecture.ARM64
        assert Architecture.from_string("aarch64") == Architecture.ARM64
        assert Architecture.from_string("i686") == Architecture.X86
        assert Architecture.from_string("i386") == Architecture.X86
        assert Architecture.from_string("x86") == Architecture.X86

    def test_architecture_from_string_invalid(self):
        """Test Architecture.from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported architecture"):
            Architecture.from_string("invalid_arch")


class TestMLIRFrontend:
    """Tests for MLIRFrontend enum."""

    def test_mlir_frontend_values(self):
        """Test all MLIRFrontend enum values exist."""
        assert MLIRFrontend.CLANG.value == "clang"
        assert MLIRFrontend.CLANGIR.value == "clangir"

    def test_mlir_frontend_from_string_valid(self):
        """Test MLIRFrontend.from_string with valid inputs."""
        assert MLIRFrontend.from_string("clang") == MLIRFrontend.CLANG
        assert MLIRFrontend.from_string("CLANG") == MLIRFrontend.CLANG
        assert MLIRFrontend.from_string("clangir") == MLIRFrontend.CLANGIR

    def test_mlir_frontend_from_string_invalid(self):
        """Test MLIRFrontend.from_string with invalid input raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported MLIR frontend"):
            MLIRFrontend.from_string("invalid")


class TestObfuscationLevel:
    """Tests for ObfuscationLevel enum."""

    def test_obfuscation_level_values(self):
        """Test all obfuscation level enum values."""
        assert ObfuscationLevel.MINIMAL == 1
        assert ObfuscationLevel.LOW == 2
        assert ObfuscationLevel.MEDIUM == 3
        assert ObfuscationLevel.HIGH == 4
        assert ObfuscationLevel.MAXIMUM == 5


class TestCryptoHashAlgorithm:
    """Tests for CryptoHashAlgorithm enum."""

    def test_crypto_hash_algorithm_values(self):
        """Test all crypto hash algorithm enum values."""
        assert CryptoHashAlgorithm.SHA256.value == "sha256"
        assert CryptoHashAlgorithm.BLAKE2B.value == "blake2b"
        assert CryptoHashAlgorithm.SIPHASH.value == "siphash"


class TestCryptoHashConfiguration:
    """Tests for CryptoHashConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for CryptoHashConfiguration."""
        config = CryptoHashConfiguration()
        assert config.enabled is False
        assert config.algorithm == CryptoHashAlgorithm.SHA256
        assert config.salt == ""
        assert config.hash_length == 12

    def test_custom_values(self):
        """Test CryptoHashConfiguration with custom values."""
        config = CryptoHashConfiguration(
            enabled=True,
            algorithm=CryptoHashAlgorithm.BLAKE2B,
            salt="test_salt",
            hash_length=16
        )
        assert config.enabled is True
        assert config.algorithm == CryptoHashAlgorithm.BLAKE2B
        assert config.salt == "test_salt"
        assert config.hash_length == 16


class TestPassConfiguration:
    """Tests for PassConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for PassConfiguration."""
        config = PassConfiguration()
        assert config.flattening is False
        assert config.substitution is False
        assert config.bogus_control_flow is False
        assert config.split is False
        assert config.linear_mba is False
        assert config.string_encrypt is False
        assert config.symbol_obfuscate is False
        assert config.constant_obfuscate is False
        assert config.address_obfuscation is False
        assert config.crypto_hash is None

    def test_enabled_passes_empty(self):
        """Test enabled_passes returns empty list when nothing enabled."""
        config = PassConfiguration()
        assert config.enabled_passes() == []

    def test_enabled_passes_with_some_enabled(self):
        """Test enabled_passes returns correct list when some passes enabled."""
        config = PassConfiguration(
            flattening=True,
            substitution=True,
            string_encrypt=True
        )
        passes = config.enabled_passes()
        assert "flattening" in passes
        assert "substitution" in passes
        assert "string-encrypt" in passes
        assert len(passes) == 3

    def test_enabled_passes_with_crypto_hash(self):
        """Test enabled_passes includes crypto-hash when enabled."""
        crypto_config = CryptoHashConfiguration(enabled=True)
        config = PassConfiguration(crypto_hash=crypto_config)
        passes = config.enabled_passes()
        assert "crypto-hash" in passes


class TestIndirectCallConfiguration:
    """Tests for IndirectCallConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for IndirectCallConfiguration."""
        config = IndirectCallConfiguration()
        assert config.enabled is False
        assert config.obfuscate_stdlib is True
        assert config.obfuscate_custom is True


class TestUPXConfiguration:
    """Tests for UPXConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for UPXConfiguration."""
        config = UPXConfiguration()
        assert config.enabled is False
        assert config.compression_level == "best"
        assert config.use_lzma is True
        assert config.preserve_original is False
        assert config.custom_upx_path is None


class TestRemarksConfiguration:
    """Tests for RemarksConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for RemarksConfiguration."""
        config = RemarksConfiguration()
        assert config.enabled is True
        assert config.format == "yaml"
        assert config.output_file is None
        assert config.pass_filter == ".*"
        assert config.with_hotness is False


class TestAntiDebugConfiguration:
    """Tests for AntiDebugConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for AntiDebugConfiguration."""
        config = AntiDebugConfiguration()
        assert config.enabled is False
        assert config.techniques == ["ptrace", "proc_status"]


class TestAdvancedConfiguration:
    """Tests for AdvancedConfiguration dataclass."""

    def test_default_values(self):
        """Test default values for AdvancedConfiguration."""
        config = AdvancedConfiguration()
        assert config.cycles == 1
        assert config.fake_loops == 0
        assert isinstance(config.indirect_calls, IndirectCallConfiguration)
        assert isinstance(config.remarks, RemarksConfiguration)
        assert isinstance(config.upx_packing, UPXConfiguration)
        assert isinstance(config.anti_debug, AntiDebugConfiguration)
        assert config.preserve_ir is True
        assert config.ir_metrics_enabled is True


class TestOutputConfiguration:
    """Tests for OutputConfiguration dataclass."""

    def test_default_values(self, tmp_dir: Path):
        """Test OutputConfiguration with default report formats."""
        config = OutputConfiguration(directory=tmp_dir)
        assert config.directory == tmp_dir
        assert "json" in config.report_formats
        assert "markdown" in config.report_formats
        assert "pdf" in config.report_formats


class TestObfuscationConfig:
    """Tests for ObfuscationConfig dataclass."""

    def test_default_values(self):
        """Test default values for ObfuscationConfig."""
        config = ObfuscationConfig()
        assert config.level == ObfuscationLevel.MEDIUM
        assert config.platform == Platform.LINUX
        assert config.architecture == Architecture.X86_64
        assert config.compiler_flags == []
        assert isinstance(config.passes, PassConfiguration)
        assert isinstance(config.advanced, AdvancedConfiguration)
        assert config.custom_pass_plugin is None
        assert config.mlir_frontend == MLIRFrontend.CLANG

    def test_from_dict_minimal(self):
        """Test ObfuscationConfig.from_dict with minimal data."""
        data = {}
        config = ObfuscationConfig.from_dict(data)
        assert config.level == ObfuscationLevel.MEDIUM
        assert config.platform == Platform.LINUX

    def test_from_dict_with_level(self):
        """Test ObfuscationConfig.from_dict with level specified."""
        data = {"level": 5}
        config = ObfuscationConfig.from_dict(data)
        assert config.level == ObfuscationLevel.MAXIMUM

    def test_from_dict_with_platform(self):
        """Test ObfuscationConfig.from_dict with platform specified."""
        data = {"platform": "windows"}
        config = ObfuscationConfig.from_dict(data)
        assert config.platform == Platform.WINDOWS

    def test_from_dict_with_passes(self):
        """Test ObfuscationConfig.from_dict with passes specified."""
        data = {
            "passes": {
                "flattening": True,
                "substitution": True,
                "string_encrypt": True
            }
        }
        config = ObfuscationConfig.from_dict(data)
        assert config.passes.flattening is True
        assert config.passes.substitution is True
        assert config.passes.string_encrypt is True

    def test_from_dict_with_advanced_config(self):
        """Test ObfuscationConfig.from_dict with advanced configuration."""
        data = {
            "advanced": {
                "cycles": 3,
                "fake_loops": 5,
                "upx_packing": {
                    "enabled": True,
                    "compression_level": "brute"
                }
            }
        }
        config = ObfuscationConfig.from_dict(data)
        assert config.advanced.cycles == 3
        assert config.advanced.fake_loops == 5
        assert config.advanced.upx_packing.enabled is True
        assert config.advanced.upx_packing.compression_level == "brute"

    def test_from_dict_with_mlir_frontend(self):
        """Test ObfuscationConfig.from_dict with mlir_frontend specified."""
        data = {"mlir_frontend": "clangir"}
        config = ObfuscationConfig.from_dict(data)
        assert config.mlir_frontend == MLIRFrontend.CLANGIR


class TestAnalyzeConfig:
    """Tests for AnalyzeConfig dataclass."""

    def test_creation(self, tmp_dir: Path):
        """Test AnalyzeConfig creation."""
        binary_path = tmp_dir / "binary"
        config = AnalyzeConfig(binary_path=binary_path)
        assert config.binary_path == binary_path
        assert config.output is None

    def test_with_output(self, tmp_dir: Path):
        """Test AnalyzeConfig with output path."""
        binary_path = tmp_dir / "binary"
        output_path = tmp_dir / "report.json"
        config = AnalyzeConfig(binary_path=binary_path, output=output_path)
        assert config.output == output_path


class TestCompareConfig:
    """Tests for CompareConfig dataclass."""

    def test_creation(self, tmp_dir: Path):
        """Test CompareConfig creation."""
        original = tmp_dir / "original"
        obfuscated = tmp_dir / "obfuscated"
        config = CompareConfig(original_binary=original, obfuscated_binary=obfuscated)
        assert config.original_binary == original
        assert config.obfuscated_binary == obfuscated
        assert config.output is None
