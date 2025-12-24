"""
Pytest configuration and shared fixtures for OAAS test suite.
"""

import base64
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Add the cmd/llvm-obfuscator directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "cmd" / "llvm-obfuscator"))


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory(prefix="oaas_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_c_source(tmp_dir: Path) -> Path:
    """Create a sample C source file for testing."""
    source = tmp_dir / "sample.c"
    source.write_text('''
#include <stdio.h>

const char* SECRET_KEY = "SuperSecret123";
static int counter = 0;

int validate_password(const char* password) {
    if (strcmp(password, SECRET_KEY) == 0) {
        counter = 0;
        return 1;
    }
    counter++;
    return 0;
}

int main() {
    printf("Test program\\n");
    return 0;
}
''', encoding="utf-8")
    return source


@pytest.fixture
def sample_cpp_source(tmp_dir: Path) -> Path:
    """Create a sample C++ source file for testing."""
    source = tmp_dir / "sample.cpp"
    source.write_text('''
#include <iostream>
#include <string>

class Authenticator {
private:
    std::string secret = "SecretPassword";
    int attempts = 0;

public:
    bool validate(const std::string& input) {
        if (input == secret) {
            attempts = 0;
            return true;
        }
        attempts++;
        return false;
    }
};

int main() {
    std::cout << "Test program" << std::endl;
    return 0;
}
''', encoding="utf-8")
    return source


@pytest.fixture
def sample_binary(tmp_dir: Path) -> Path:
    """Create a mock ELF binary file for testing."""
    binary = tmp_dir / "sample_binary"
    # ELF magic header + some content
    binary.write_bytes(b"\x7fELF" + b"\x00" * 60 + b"fake binary content")
    return binary


@pytest.fixture
def sample_pe_binary(tmp_dir: Path) -> Path:
    """Create a mock PE binary file for testing."""
    binary = tmp_dir / "sample.exe"
    # PE magic header
    binary.write_bytes(b"MZ" + b"\x00" * 62 + b"fake PE content")
    return binary


@pytest.fixture
def base64_source(sample_c_source: Path) -> str:
    """Return base64 encoded source code."""
    return base64.b64encode(sample_c_source.read_bytes()).decode("ascii")


@pytest.fixture(autouse=True)
def set_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for testing."""
    monkeypatch.setenv("OBFUSCATOR_API_KEY", "test-api-key")
    monkeypatch.setenv("OBFUSCATOR_DISABLE_AUTH", "false")


@pytest.fixture
def mock_llvm_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock LLVM tool availability for testing without actual LLVM installation."""
    from core import utils

    def fake_tool_exists(tool_name: str) -> bool:
        # Pretend common tools exist
        return tool_name in ["clang", "clang++", "opt", "llvm-nm", "nm", "objdump"]

    def fake_run_command(*args, **kwargs):
        return 0, "", ""

    monkeypatch.setattr(utils, "tool_exists", fake_tool_exists)
    monkeypatch.setattr(utils, "run_command", fake_run_command)
