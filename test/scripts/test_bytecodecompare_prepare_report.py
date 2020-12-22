#!/usr/bin/env python

import json
import unittest
from pathlib import Path
from textwrap import dedent

from unittest_helpers import LIBSOLIDITY_TEST_DIR, load_fixture, load_libsolidity_test_case

from bytecodecompare.prepare_report import CompilerInterface, FileReport, ContractReport, SMTUse
from bytecodecompare.prepare_report import load_source, parse_cli_output, parse_standard_json_output, prepare_compiler_input


SMT_SMOKE_TEST_SOL_PATH = LIBSOLIDITY_TEST_DIR / 'smtCheckerTests/simple/smoke_test.sol'
SMT_SMOKE_TEST_SOL_CODE = load_libsolidity_test_case(SMT_SMOKE_TEST_SOL_PATH)

SYNTAX_SMOKE_TEST_SOL_PATH = LIBSOLIDITY_TEST_DIR / 'syntaxTests/smoke_test.sol'
SYNTAX_SMOKE_TEST_SOL_CODE = load_libsolidity_test_case(SYNTAX_SMOKE_TEST_SOL_PATH)

LIBRARY_INHERITED2_SOL_JSON_OUTPUT = load_fixture('library_inherited2_sol_json_output.json')
LIBRARY_INHERITED2_SOL_CLI_OUTPUT = load_fixture('library_inherited2_sol_cli_output.txt')

UNKNOWN_PRAGMA_SOL_JSON_OUTPUT = load_fixture('unknown_pragma_sol_json_output.json')
UNKNOWN_PRAGMA_SOL_CLI_OUTPUT = load_fixture('unknown_pragma_sol_cli_output.txt')


class TestPrepareReport_FileReport(unittest.TestCase):
    def test_format_report(self):
        report = FileReport(
            file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
            contract_reports=[
                ContractReport(
                    contract_name='A',
                    file_name=Path('syntaxTests/smoke_test.sol'),
                    bytecode=None,
                    metadata=None,
                ),
                ContractReport(
                    contract_name='B',
                    file_name=Path('syntaxTests/smoke_test.sol'),
                    bytecode=None,
                    metadata='{"language":"Solidity"}',
                ),
                ContractReport(
                    contract_name='Lib',
                    file_name=Path('syntaxTests/smoke_test.sol'),
                    bytecode='60566050600b828282398051',
                    metadata=None,
                ),
            ]
        )

        expected_output = dedent("""\
            syntaxTests/scoping/library_inherited2.sol:A <NO BYTECODE>
            syntaxTests/scoping/library_inherited2.sol:A <NO METADATA>
            syntaxTests/scoping/library_inherited2.sol:B <NO BYTECODE>
            syntaxTests/scoping/library_inherited2.sol:B {"language":"Solidity"}
            syntaxTests/scoping/library_inherited2.sol:Lib 60566050600b828282398051
            syntaxTests/scoping/library_inherited2.sol:Lib <NO METADATA>
        """)

        self.assertEqual(report.format_report(), expected_output)

    def test_format_report_should_print_error_if_contract_report_list_is_missing(self):
        report = FileReport(file_name=Path('file.sol'), contract_reports=None)

        expected_output = dedent("""\
            file.sol: <ERROR>
        """)

        self.assertEqual(report.format_report(), expected_output)

    def test_format_report_should_not_print_anything_if_contract_report_list_is_empty(self):
        report = FileReport(file_name=Path('file.sol'), contract_reports=[])

        self.assertEqual(report.format_report(), '')


class TestPrepareReport(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 10000

    def test_load_source_should_strip_smt_pragmas_if_requested(self):
        expected_file_content = dedent("""\

            contract C {
            }
        """)

        self.assertEqual(load_source(SMT_SMOKE_TEST_SOL_PATH, SMTUse.STRIP_PRAGMAS), expected_file_content)

    def test_load_source_should_not_strip_smt_pragmas_if_not_requested(self):
        self.assertEqual(load_source(SMT_SMOKE_TEST_SOL_PATH, SMTUse.DISABLE), SMT_SMOKE_TEST_SOL_CODE)
        self.assertEqual(load_source(SMT_SMOKE_TEST_SOL_PATH, SMTUse.PRESERVE), SMT_SMOKE_TEST_SOL_CODE)

    def test_prepare_compiler_input_should_work_with_standard_json_interface(self):
        expected_compiler_input = {
            'language': 'Solidity',
            'sources': {
                str(SMT_SMOKE_TEST_SOL_PATH): {'content': SMT_SMOKE_TEST_SOL_CODE},
            },
            'settings': {
                'optimizer': {'enabled': True},
                'outputSelection': {'*': {'*': ['evm.bytecode.object', 'metadata']}},
                'modelChecker': {'engine': 'none'},
            }
        }

        (command_line, compiler_input) = prepare_compiler_input(
            Path('solc'),
            SMT_SMOKE_TEST_SOL_PATH,
            optimize=True,
            interface=CompilerInterface.STANDARD_JSON,
            smt_use=SMTUse.DISABLE
        )

        self.assertEqual(command_line, ['solc', '--standard-json'])
        self.assertEqual(json.loads(compiler_input), expected_compiler_input)

    def test_prepare_compiler_input_should_work_with_cli_interface(self):
        (command_line, compiler_input) = prepare_compiler_input(
            Path('solc'),
            SMT_SMOKE_TEST_SOL_PATH,
            optimize=True,
            interface=CompilerInterface.CLI,
            smt_use=SMTUse.DISABLE
        )

        self.assertEqual(command_line, ['solc', str(SMT_SMOKE_TEST_SOL_PATH), '--bin', '--metadata', '--optimize', '--model-checker-engine', 'none'])
        self.assertEqual(compiler_input, SMT_SMOKE_TEST_SOL_CODE)

    def test_parse_standard_json_output(self):
        expected_report = FileReport(
            file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
            contract_reports=[
                ContractReport(
                    contract_name='A',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='6080604052348015600f57600080fd5b50603f80601d6000396000f3fe6080604052600080fdfea264697066735822122086e727f29d40b264a19bbfcad38d64493dca4bab5dbba8c82ffdaae389d2bba064736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"A"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
                ContractReport(
                    contract_name='B',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='608060405234801561001057600080fd5b506101cc806100206000396000f3fe608060405234801561001057600080fd5b506004361061002b5760003560e01c80630423a13214610030575b600080fd5b61004a6004803603810190610045919061009d565b610060565b60405161005791906100d5565b60405180910390f35b600061006b82610072565b9050919050565b6000602a8261008191906100f0565b9050919050565b6000813590506100978161017f565b92915050565b6000602082840312156100af57600080fd5b60006100bd84828501610088565b91505092915050565b6100cf81610146565b82525050565b60006020820190506100ea60008301846100c6565b92915050565b60006100fb82610146565b915061010683610146565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0382111561013b5761013a610150565b5b828201905092915050565b6000819050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b61018881610146565b811461019357600080fd5b5056fea2646970667358221220104c345633313efe410492448844d96d78452c3044ce126b5e041b7fbeaa790064736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[{"inputs":[{"internalType":"uint256","name":"value","type":"uint256"}],"name":"bar","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"}],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"B"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
                ContractReport(
                    contract_name='Lib',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='60566050600b82828239805160001a6073146043577f4e487b7100000000000000000000000000000000000000000000000000000000600052600060045260246000fd5b30600052607381538281f3fe73000000000000000000000000000000000000000030146080604052600080fdfea26469706673582212207f9515e2263fa71a7984707e2aefd82241fac15c497386ca798b526f14f8ba6664736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"Lib"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
            ]
        )

        self.assertEqual(parse_standard_json_output(Path('syntaxTests/scoping/library_inherited2.sol'), LIBRARY_INHERITED2_SOL_JSON_OUTPUT), expected_report)

    def test_parse_standard_json_output_should_report_error_on_compiler_errors(self):
        expected_report = FileReport(file_name=Path('syntaxTests/pragma/unknown_pragma.sol'), contract_reports=None)

        self.assertEqual(parse_standard_json_output(Path('syntaxTests/pragma/unknown_pragma.sol'), UNKNOWN_PRAGMA_SOL_JSON_OUTPUT), expected_report)

    def test_parse_standard_json_output_should_report_error_on_empty_json(self):
        expected_report = FileReport(file_name=Path('file.sol'), contract_reports=None)

        self.assertEqual(parse_standard_json_output(Path('file.sol'), '{}'), expected_report)

    def test_parse_standard_json_output_should_report_error_if_contracts_is_empty(self):
        compiler_output = '{"contracts": {}}'

        expected_report = FileReport(file_name=Path('contract.sol'), contract_reports=None)

        self.assertEqual(parse_standard_json_output(Path('contract.sol'), compiler_output), expected_report)

    def test_parse_standard_json_output_should_report_error_if_every_file_has_no_contracts(self):
        compiler_output = dedent("""\
            {
                "contracts": {
                    "contract1.sol": {},
                    "contract2.sol": {}
                }
            }
        """)

        expected_report = FileReport(file_name=Path('contract.sol'), contract_reports=None)

        self.assertEqual(parse_standard_json_output(Path('contract.sol'), compiler_output), expected_report)

    def test_parse_standard_json_output_should_not_report_error_if_there_is_at_least_one_file_with_contracts(self):
        compiler_output = dedent("""\
            {
                "contracts": {
                    "contract1.sol": {"A": {}},
                    "contract2.sol": {}
                }
            }
        """)

        expected_report = FileReport(
            file_name=Path('contract.sol'),
            contract_reports=[ContractReport(contract_name='A', file_name=Path('contract1.sol'), bytecode=None, metadata=None)]
        )

        self.assertEqual(parse_standard_json_output(Path('contract.sol'), compiler_output), expected_report)

    def test_parse_cli_output(self):
        expected_report = FileReport(
            file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
            contract_reports=[
                ContractReport(
                    contract_name='A',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='6080604052348015600f57600080fd5b50603f80601d6000396000f3fe6080604052600080fdfea264697066735822122086e727f29d40b264a19bbfcad38d64493dca4bab5dbba8c82ffdaae389d2bba064736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"A"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
                ContractReport(
                    contract_name='B',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='608060405234801561001057600080fd5b506101cc806100206000396000f3fe608060405234801561001057600080fd5b506004361061002b5760003560e01c80630423a13214610030575b600080fd5b61004a6004803603810190610045919061009d565b610060565b60405161005791906100d5565b60405180910390f35b600061006b82610072565b9050919050565b6000602a8261008191906100f0565b9050919050565b6000813590506100978161017f565b92915050565b6000602082840312156100af57600080fd5b60006100bd84828501610088565b91505092915050565b6100cf81610146565b82525050565b60006020820190506100ea60008301846100c6565b92915050565b60006100fb82610146565b915061010683610146565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0382111561013b5761013a610150565b5b828201905092915050565b6000819050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b61018881610146565b811461019357600080fd5b5056fea2646970667358221220104c345633313efe410492448844d96d78452c3044ce126b5e041b7fbeaa790064736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[{"inputs":[{"internalType":"uint256","name":"value","type":"uint256"}],"name":"bar","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"}],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"B"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
                ContractReport(
                    contract_name='Lib',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='60566050600b82828239805160001a6073146043577f4e487b7100000000000000000000000000000000000000000000000000000000600052600060045260246000fd5b30600052607381538281f3fe73000000000000000000000000000000000000000030146080604052600080fdfea26469706673582212207f9515e2263fa71a7984707e2aefd82241fac15c497386ca798b526f14f8ba6664736f6c63430008000033',
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"Lib"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
            ]
        )

        self.assertEqual(parse_cli_output(Path('syntaxTests/scoping/library_inherited2.sol'), LIBRARY_INHERITED2_SOL_CLI_OUTPUT), expected_report)

    def test_parse_cli_output_should_report_error_on_compiler_errors(self):
        expected_report = FileReport(file_name=Path('syntaxTests/pragma/unknown_pragma.sol'), contract_reports=None)

        self.assertEqual(parse_cli_output(Path('syntaxTests/pragma/unknown_pragma.sol'), UNKNOWN_PRAGMA_SOL_CLI_OUTPUT), expected_report)

    def test_parse_cli_output_should_report_error_on_empty_output(self):
        expected_report = FileReport(file_name=Path('file.sol'), contract_reports=None)

        self.assertEqual(parse_cli_output(Path('file.sol'), ''), expected_report)

    def test_parse_cli_output_should_report_missing_bytecode_and_metadata(self):
        compiler_output = dedent("""\
            ======= syntaxTests/scoping/library_inherited2.sol:A =======
            ======= syntaxTests/scoping/library_inherited2.sol:B =======
            608060405234801561001057600080fd5b506101cc806100206000396000f3fe608060405234801561001057600080fd5b506004361061002b5760003560e01c80630423a13214610030575b600080fd5b61004a6004803603810190610045919061009d565b610060565b60405161005791906100d5565b60405180910390f35b600061006b82610072565b9050919050565b6000602a8261008191906100f0565b9050919050565b6000813590506100978161017f565b92915050565b6000602082840312156100af57600080fd5b60006100bd84828501610088565b91505092915050565b6100cf81610146565b82525050565b60006020820190506100ea60008301846100c6565b92915050565b60006100fb82610146565b915061010683610146565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0382111561013b5761013a610150565b5b828201905092915050565b6000819050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b61018881610146565b811461019357600080fd5b5056fea2646970667358221220104c345633313efe410492448844d96d78452c3044ce126b5e041b7fbeaa790064736f6c63430008000033
            Metadata:
            {"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[{"inputs":[{"internalType":"uint256","name":"value","type":"uint256"}],"name":"bar","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"}],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"B"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}

            ======= syntaxTests/scoping/library_inherited2.sol:Lib =======
            Binary:
            60566050600b82828239805160001a6073146043577f4e487b7100000000000000000000000000000000000000000000000000000000600052600060045260246000fd5b30600052607381538281f3fe73000000000000000000000000000000000000000030146080604052600080fdfea26469706673582212207f9515e2263fa71a7984707e2aefd82241fac15c497386ca798b526f14f8ba6664736f6c63430008000033
            Metadata:
        """)

        expected_report = FileReport(
            file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
            contract_reports=[
                ContractReport(
                    contract_name='A',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode=None,
                    metadata=None,
                ),
                ContractReport(
                    contract_name='B',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode=None,
                    metadata='{"compiler":{"version":"0.8.0+commit.c7dfd78e"},"language":"Solidity","output":{"abi":[{"inputs":[{"internalType":"uint256","name":"value","type":"uint256"}],"name":"bar","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"pure","type":"function"}],"devdoc":{"kind":"dev","methods":{},"version":1},"userdoc":{"kind":"user","methods":{},"version":1}},"settings":{"compilationTarget":{"syntaxTests/scoping/library_inherited2.sol":"B"},"evmVersion":"istanbul","libraries":{},"metadata":{"bytecodeHash":"ipfs"},"optimizer":{"enabled":false,"runs":200},"remappings":[]},"sources":{"syntaxTests/scoping/library_inherited2.sol":{"keccak256":"0xd0619f00638fdfea187368965615dbd599fead93dd14b6558725e85ec7011d96","urls":["bzz-raw://ec7af066be66a223f0d25ba3bf9ba6dc103e1a57531a66a38a5ca2b6ce172f55","dweb:/ipfs/QmW1NrqQNhnY1Tkgr3Z9oM8buCGLUJCJVCDTVejJTT5Vet"]}},"version":1}',
                ),
                ContractReport(
                    contract_name='Lib',
                    file_name=Path('syntaxTests/scoping/library_inherited2.sol'),
                    bytecode='60566050600b82828239805160001a6073146043577f4e487b7100000000000000000000000000000000000000000000000000000000600052600060045260246000fd5b30600052607381538281f3fe73000000000000000000000000000000000000000030146080604052600080fdfea26469706673582212207f9515e2263fa71a7984707e2aefd82241fac15c497386ca798b526f14f8ba6664736f6c63430008000033',
                    metadata=None,
                ),
            ]
        )

        self.assertEqual(parse_cli_output(Path('syntaxTests/scoping/library_inherited2.sol'), compiler_output), expected_report)
