"""Unit tests for the AST and regex symbol extraction."""

import pytest
from pathlib import Path
from harness.repository.symbols import (
    FileSymbols,
    ImportItem,
    Symbol,
    SymbolExtractor,
    SymbolType,
)


def test_python_symbol_extraction():
    code = """
import os
from typing import List, Optional
from harness.model import ModelGateway as Gateway

MAX_RETRIES = 5

class AuthManager:
    \"\"\"Manages user authentication and token creation.\"\"\"

    def __init__(self, secret: str) -> None:
        self.secret = secret

    async def authenticate(self, username: str, password_hash: str) -> bool:
        return self._verify(username, password_hash)

    def _verify(self, u: str, p: str) -> bool:
        return True

def standalone_helper(val: int) -> str:
    \"\"\"Helper docstring.\"\"\"
    return str(val)
"""
    symbols_res = SymbolExtractor.extract_from_code(code, file_path="auth_service.py")
    assert symbols_res.parse_error is None

    # Check imports
    imports = {imp.imported_name: imp for imp in symbols_res.imports}
    assert "os" in imports
    assert "List" in imports
    assert "ModelGateway" in imports
    assert imports["ModelGateway"].alias == "Gateway"
    assert imports["ModelGateway"].source_module == "harness.model"

    # Check constants
    sym_map = {s.name: s for s in symbols_res.symbols}
    assert "MAX_RETRIES" in sym_map
    assert sym_map["MAX_RETRIES"].symbol_type == SymbolType.VARIABLE

    # Check class
    assert "AuthManager" in sym_map
    auth_cls = sym_map["AuthManager"]
    assert auth_cls.symbol_type == SymbolType.CLASS
    assert "Manages user authentication" in auth_cls.docstring

    # Check methods
    assert "AuthManager.__init__" in sym_map
    assert "AuthManager.authenticate" in sym_map
    auth_method = sym_map["AuthManager.authenticate"]
    assert auth_method.symbol_type == SymbolType.METHOD
    assert "async def authenticate" in auth_method.signature
    assert "username: str" in auth_method.parameters[1]

    # Check standalone function
    assert "standalone_helper" in sym_map
    helper = sym_map["standalone_helper"]
    assert helper.symbol_type == SymbolType.FUNCTION
    assert "val: int" in helper.parameters[0]
    assert helper.return_type == "str"


def test_javascript_symbol_extraction():
    js_code = """
import { useState, useEffect } from 'react';
import axios from 'axios';

export class UserService {
    // service
}

export function fetchUserProfile(userId) {
    return axios.get(`/users/${userId}`);
}

const loginHandler = (email, password) => {
    return true;
};
"""
    symbols_res = SymbolExtractor.extract_from_code(js_code, file_path="userService.js")
    assert symbols_res.parse_error is None

    sym_names = {s.name for s in symbols_res.symbols}
    assert "UserService" in sym_names
    assert "fetchUserProfile" in sym_names
    assert "loginHandler" in sym_names

    imports = {imp.source_module for imp in symbols_res.imports}
    assert "react" in imports
    assert "axios" in imports
