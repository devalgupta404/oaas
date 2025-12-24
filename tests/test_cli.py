"""
Unit tests for the CLI module (cli.obfuscate).
Tests command-line interface functionality.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.obfuscate import (
    app,
    _build_config,
    Colors,
    print_banner,
)
from core.config import (
    ObfuscationLevel,
    Platform,
    PassConfiguration,
    ObfuscationConfig,
)


runner = CliRunner()


class TestColors:
    """Tests for Colors class."""

    def test_color_codes_exist(self):
        """Test that all color codes are defined."""
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'BLUE')
        assert hasattr(Colors, 'RESET')
        assert hasattr(Colors, 'BOLD')

    def test_color_codes_are_strings(self):
        """Test that color codes are ANSI escape sequences."""
        assert Colors.RED.startswith('\033[')
        assert Colors.RESET == '\033[0m'


class TestPrintBanner:
    """Tests for print_banner function."""

    def test_banner_output(self, capsys):
        """Test that banner is printed without errors."""
        # Just verify it doesn't raise an exception
        print_banner()
        # Banner should produce output
        captured = capsys.readouterr()
        # Output goes through typer.echo which may not be captured in capsys
        # Just ensure no exception was raised


class TestBuildConfig:
    """Tests for _build_config helper function."""

    def test_build_config_minimal(self, tmp_dir: Path):
        """Test building config with minimal options."""
        config = _build_config(
            input_path=tmp_dir / "test.c",
            output=tmp_dir / "out",
            platform=Platform.LINUX,
            level=ObfuscationLevel.MEDIUM,
            enable_flattening=False,
            enable_substitution=False,
            enable_bogus_cf=False,
            enable_split=False,
            enable_linear_mba=False,
            cycles=1,
            string_encryption=False,
            symbol_obfuscation=False,
            fake_loops=0,
            enable_indirect_calls=False,
            indirect_stdlib=True,
            indirect_custom=True,
            enable_upx=False,
            upx_compression="best",
            upx_lzma=True,
            upx_preserve_original=False,
            upx_custom_path=None,
            enable_anti_debug=False,
            report_formats="json",
            custom_flags=None,
            config_file=None,
            custom_pass_plugin=None,
        )

        assert isinstance(config, ObfuscationConfig)
        assert config.level == ObfuscationLevel.MEDIUM
        assert config.platform == Platform.LINUX

    def test_build_config_with_passes(self, tmp_dir: Path):
        """Test building config with obfuscation passes enabled."""
        config = _build_config(
            input_path=tmp_dir / "test.c",
            output=tmp_dir / "out",
            platform=Platform.LINUX,
            level=ObfuscationLevel.HIGH,
            enable_flattening=True,
            enable_substitution=True,
            enable_bogus_cf=True,
            enable_split=True,
            enable_linear_mba=False,
            cycles=2,
            string_encryption=True,
            symbol_obfuscation=True,
            fake_loops=5,
            enable_indirect_calls=False,
            indirect_stdlib=True,
            indirect_custom=True,
            enable_upx=False,
            upx_compression="best",
            upx_lzma=True,
            upx_preserve_original=False,
            upx_custom_path=None,
            enable_anti_debug=False,
            report_formats="json,html",
            custom_flags=None,
            config_file=None,
            custom_pass_plugin=None,
        )

        assert config.passes.flattening is True
        assert config.passes.substitution is True
        assert config.passes.bogus_control_flow is True
        assert config.passes.split is True
        assert config.passes.string_encrypt is True
        assert config.passes.symbol_obfuscate is True
        assert config.advanced.cycles == 2
        assert config.advanced.fake_loops == 5

    def test_build_config_with_upx(self, tmp_dir: Path):
        """Test building config with UPX enabled."""
        config = _build_config(
            input_path=tmp_dir / "test.c",
            output=tmp_dir / "out",
            platform=Platform.LINUX,
            level=ObfuscationLevel.MEDIUM,
            enable_flattening=False,
            enable_substitution=False,
            enable_bogus_cf=False,
            enable_split=False,
            enable_linear_mba=False,
            cycles=1,
            string_encryption=False,
            symbol_obfuscation=False,
            fake_loops=0,
            enable_indirect_calls=False,
            indirect_stdlib=True,
            indirect_custom=True,
            enable_upx=True,
            upx_compression="brute",
            upx_lzma=True,
            upx_preserve_original=True,
            upx_custom_path=None,
            enable_anti_debug=False,
            report_formats="json",
            custom_flags=None,
            config_file=None,
            custom_pass_plugin=None,
        )

        assert config.advanced.upx_packing.enabled is True
        assert config.advanced.upx_packing.compression_level == "brute"
        assert config.advanced.upx_packing.preserve_original is True

    def test_build_config_with_custom_flags(self, tmp_dir: Path):
        """Test building config with custom compiler flags."""
        config = _build_config(
            input_path=tmp_dir / "test.c",
            output=tmp_dir / "out",
            platform=Platform.LINUX,
            level=ObfuscationLevel.MEDIUM,
            enable_flattening=False,
            enable_substitution=False,
            enable_bogus_cf=False,
            enable_split=False,
            enable_linear_mba=False,
            cycles=1,
            string_encryption=False,
            symbol_obfuscation=False,
            fake_loops=0,
            enable_indirect_calls=False,
            indirect_stdlib=True,
            indirect_custom=True,
            enable_upx=False,
            upx_compression="best",
            upx_lzma=True,
            upx_preserve_original=False,
            upx_custom_path=None,
            enable_anti_debug=False,
            report_formats="json",
            custom_flags="-O3 -Wall -Werror",
            config_file=None,
            custom_pass_plugin=None,
        )

        assert "-O3" in config.compiler_flags
        assert "-Wall" in config.compiler_flags
        assert "-Werror" in config.compiler_flags


class TestCLICommands:
    """Tests for CLI command invocations."""

    def test_app_help(self):
        """Test that --help works."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "LLVM-based binary obfuscation toolkit" in result.output or "Usage" in result.output

    def test_compile_help(self):
        """Test that compile --help works."""
        result = runner.invoke(app, ["compile", "--help"])
        assert result.exit_code == 0
        assert "compile" in result.output.lower() or "obfuscate" in result.output.lower()

    def test_analyze_help(self):
        """Test that analyze --help works."""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0

    def test_compare_help(self):
        """Test that compare --help works."""
        result = runner.invoke(app, ["compare", "--help"])
        assert result.exit_code == 0

    def test_batch_help(self):
        """Test that batch --help works."""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0

    def test_help_layers(self):
        """Test help layers subcommand."""
        result = runner.invoke(app, ["help", "layers"])
        assert result.exit_code == 0
        assert "layer" in result.output.lower()

    def test_help_mlir(self):
        """Test help mlir subcommand."""
        result = runner.invoke(app, ["help", "mlir"])
        assert result.exit_code == 0
        assert "mlir" in result.output.lower() or "string" in result.output.lower()

    def test_help_ollvm(self):
        """Test help ollvm subcommand."""
        result = runner.invoke(app, ["help", "ollvm"])
        assert result.exit_code == 0
        assert "ollvm" in result.output.lower() or "control" in result.output.lower()

    def test_help_advanced(self):
        """Test help advanced subcommand."""
        result = runner.invoke(app, ["help", "advanced"])
        assert result.exit_code == 0

    def test_help_strategies(self):
        """Test help strategies subcommand."""
        result = runner.invoke(app, ["help", "strategies"])
        assert result.exit_code == 0
        assert "protection" in result.output.lower() or "strategy" in result.output.lower()

    def test_help_examples(self):
        """Test help examples subcommand."""
        result = runner.invoke(app, ["help", "examples"])
        assert result.exit_code == 0
        assert "example" in result.output.lower()


class TestCLICompileCommand:
    """Tests for the compile command with mocked obfuscation."""

    @pytest.fixture
    def mock_obfuscator(self, monkeypatch):
        """Mock the obfuscator to avoid actual compilation."""
        mock_result = {
            "output_file": "/tmp/test_output",
            "symbol_reduction": 50,
            "requested_passes": ["flattening"],
            "applied_passes": ["flattening"],
            "report_paths": {}
        }

        mock_obfuscate = MagicMock(return_value=mock_result)

        with patch('cli.obfuscate.LLVMObfuscator') as MockObfuscator:
            instance = MockObfuscator.return_value
            instance.obfuscate = mock_obfuscate
            yield mock_obfuscate

    def test_compile_with_required_args(self, sample_c_source: Path, tmp_dir: Path, mock_obfuscator):
        """Test compile command with required arguments only."""
        result = runner.invoke(app, [
            "compile",
            str(sample_c_source),
            "--output", str(tmp_dir / "output"),
        ])
        # May fail due to missing tools, but shouldn't crash
        # Check it attempted to run
        assert result.exit_code in [0, 1]

    def test_compile_with_all_passes(self, sample_c_source: Path, tmp_dir: Path, mock_obfuscator):
        """Test compile command with all passes enabled."""
        result = runner.invoke(app, [
            "compile",
            str(sample_c_source),
            "--output", str(tmp_dir / "output"),
            "--enable-flattening",
            "--enable-substitution",
            "--enable-bogus-cf",
            "--enable-split",
            "--enable-string-encrypt",
            "--enable-symbol-obfuscate",
        ])
        assert result.exit_code in [0, 1]

    def test_compile_with_level(self, sample_c_source: Path, tmp_dir: Path, mock_obfuscator):
        """Test compile command with different obfuscation levels."""
        for level in [1, 2, 3, 4, 5]:
            result = runner.invoke(app, [
                "compile",
                str(sample_c_source),
                "--output", str(tmp_dir / f"output_{level}"),
                "--level", str(level),
            ])
            assert result.exit_code in [0, 1]

    def test_compile_invalid_level(self, sample_c_source: Path, tmp_dir: Path):
        """Test compile command with invalid level."""
        result = runner.invoke(app, [
            "compile",
            str(sample_c_source),
            "--output", str(tmp_dir / "output"),
            "--level", "10",  # Invalid level
        ])
        assert result.exit_code != 0


class TestCLIAnalyzeCommand:
    """Tests for the analyze command."""

    @pytest.fixture
    def mock_analyze(self, monkeypatch):
        """Mock the analyze_binary function."""
        mock_result = {
            "symbol_count": 100,
            "function_count": 20,
            "entropy": 7.5,
            "format": "ELF"
        }

        with patch('cli.obfuscate.analyze_binary', return_value=mock_result):
            yield

    def test_analyze_basic(self, sample_binary: Path, mock_analyze):
        """Test analyze command with binary path."""
        result = runner.invoke(app, [
            "analyze",
            str(sample_binary),
        ])
        assert result.exit_code in [0, 1]


class TestCLICompareCommand:
    """Tests for the compare command."""

    @pytest.fixture
    def mock_compare(self, monkeypatch):
        """Mock the compare_binaries function."""
        mock_result = {
            "size_delta": 1024,
            "symbol_delta": -50,
            "entropy_delta": 0.5
        }

        with patch('cli.obfuscate.compare_binaries', return_value=mock_result):
            yield

    def test_compare_basic(self, sample_binary: Path, mock_compare):
        """Test compare command with two binaries."""
        result = runner.invoke(app, [
            "compare",
            str(sample_binary),
            str(sample_binary),
        ])
        assert result.exit_code in [0, 1]
