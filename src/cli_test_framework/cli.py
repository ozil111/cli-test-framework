#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI Test Framework - Command Line Interface

This module provides the main command-line interface for the CLI Testing Framework.
"""

import argparse
import sys
import os
from pathlib import Path

from .runners import JSONRunner, ParallelJSONRunner, YAMLRunner


def create_parser():
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        description="CLI Testing Framework - A powerful tool for testing command-line applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cli-test run test_cases.json
  cli-test run test_cases.json --parallel --workers 4
  cli-test run test_cases.yaml --workspace /path/to/project
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run test cases from a configuration file')
    run_parser.add_argument('config_file', help='Path to the test configuration file (JSON or YAML)')
    run_parser.add_argument('--workspace', '-w', help='Working directory for test execution')
    run_parser.add_argument('--parallel', '-p', action='store_true', help='Run tests in parallel')
    run_parser.add_argument('--workers', type=int, help='Number of parallel workers (default: CPU count)')
    run_parser.add_argument('--execution-mode', choices=['thread', 'process'], default='thread',
                           help='Parallel execution mode (default: thread)')
    run_parser.add_argument('--output-format', choices=['text', 'json', 'html'], default='text',
                           help='Output format for test results')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    run_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    return parser


def run_tests(args):
    """Run tests based on command line arguments"""
    config_file = Path(args.config_file)
    
    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}")
        return False
    
    # Determine file type
    file_ext = config_file.suffix.lower()
    
    try:
        if args.parallel:
            # Use parallel runner
            runner = ParallelJSONRunner(
                config_file=str(config_file),
                workspace=args.workspace,
                max_workers=args.workers,
                execution_mode=args.execution_mode
            )
        else:
            # Use appropriate single-threaded runner
            if file_ext in ['.json']:
                runner = JSONRunner(
                    config_file=str(config_file),
                    workspace=args.workspace
                )
            elif file_ext in ['.yaml', '.yml']:
                runner = YAMLRunner(
                    config_file=str(config_file),
                    workspace=args.workspace
                )
            else:
                print(f"Error: Unsupported configuration file format: {file_ext}")
                return False
        
        # Run tests
        print(f"Running tests from: {config_file}")
        if args.parallel:
            print(f"Parallel mode: {args.execution_mode}, workers: {args.workers or 'auto'}")
        
        success = runner.run_tests()
        
        # Output results
        if hasattr(runner, 'results'):
            results = runner.results
            print(f"\nTest Results:")
            print(f"Total tests: {results.get('total_tests', 0)}")
            print(f"Passed: {results.get('passed', 0)}")
            print(f"Failed: {results.get('failed', 0)}")
            
            if args.verbose and 'details' in results:
                print("\nDetailed Results:")
                for result in results['details']:
                    status_symbol = "✓" if result['status'] == 'passed' else "✗"
                    print(f"  {status_symbol} {result['name']}: {result['status']}")
                    if result['status'] == 'failed' and result.get('message'):
                        print(f"    Error: {result['message']}")
        
        return success
        
    except Exception as e:
        print(f"Error running tests: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main entry point for the CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == 'run':
        success = run_tests(args)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main() 