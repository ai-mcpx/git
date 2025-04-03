#!/usr/bin/env python3
"""
Test client for the MCP Git Server
Provides automated testing of server functionality
"""

import json
import socket
import sys
import time
import argparse
from typing import Dict, Any, Optional, List, Tuple


class MCPGitClient:
    """Client for interacting with the MCP Git Server"""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        """
        Initialize the MCP Git client
        
        Args:
            host: Server hostname
            port: Server port
        """
        self.host = host
        self.port = port
    
    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a command to the MCP Git Server
        
        Args:
            command: Git command to execute
            params: Command parameters (dict)
            
        Returns:
            Server response as a dictionary
        """
        if params is None:
            params = {}
            
        # Create request message
        request = {
            "command": command,
            "params": params
        }
        
        # Connect to server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            client.connect((self.host, self.port))
            
            # Serialize and send request
            request_json = json.dumps(request).encode('utf-8')
            length = len(request_json).to_bytes(4, byteorder='big')
            client.sendall(length + request_json)
            
            # Receive response length
            response_len_bytes = client.recv(4)
            response_len = int.from_bytes(response_len_bytes, byteorder='big')
            
            # Receive response data
            response_data = b""
            while len(response_data) < response_len:
                chunk = client.recv(min(4096, response_len - len(response_data)))
                if not chunk:
                    break
                response_data += chunk
                
            # Parse response
            response = json.loads(response_data.decode('utf-8'))
            return response
            
        finally:
            client.close()


class MCPGitTester:
    """Test suite for the MCP Git Server"""
    
    def __init__(self, client: MCPGitClient):
        """
        Initialize the tester with a client
        
        Args:
            client: MCPGitClient instance
        """
        self.client = client
        self.tests_run = 0
        self.tests_passed = 0
    
    def run_test(self, name: str, command: str, params: Optional[Dict[str, Any]] = None, 
                 expected_status: str = "success", validation_func: Optional[callable] = None) -> bool:
        """
        Run a single test against the server
        
        Args:
            name: Test name
            command: Git command to execute
            params: Command parameters
            expected_status: Expected status in response ("success" or "error")
            validation_func: Optional function to validate response data
            
        Returns:
            True if test passed, False otherwise
        """
        self.tests_run += 1
        print(f"\nTest {self.tests_run}: {name}")
        print(f"  Command: {command}")
        print(f"  Params: {params}")
        
        try:
            response = self.client.send_command(command, params)
            status = response.get("status")
            
            # Check status
            status_ok = status == expected_status
            if status_ok:
                print(f"  ✓ Status: {status} (as expected)")
            else:
                print(f"  ✗ Status: {status} (expected {expected_status})")
            
            # Run custom validation if provided
            validation_ok = True
            if validation_func:
                validation_ok = validation_func(response)
            
            # Overall test result
            if status_ok and validation_ok:
                print("  ✓ Test passed")
                self.tests_passed += 1
                return True
            else:
                print("  ✗ Test failed")
                return False
                
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
            return False
    
    def run_test_suite(self) -> Tuple[int, int]:
        """
        Run the complete test suite
        
        Returns:
            Tuple of (tests_passed, tests_run)
        """
        # Test basic connectivity
        self.run_test(
            name="Basic connectivity - Status",
            command="status"
        )
        
        # Test invalid command
        self.run_test(
            name="Invalid command",
            command="invalid_command",
            expected_status="error"
        )
        
        # Test log with default parameters
        self.run_test(
            name="Get commit log (default)",
            command="log",
            validation_func=lambda r: "data" in r and isinstance(r["data"].get("commits", []), list)
        )
        
        # Test log with count parameter
        self.run_test(
            name="Get commit log with count",
            command="log",
            params={"count": 5},
            validation_func=lambda r: len(r.get("data", {}).get("commits", [])) <= 5
        )
        
        # Test branch list
        self.run_test(
            name="List branches",
            command="branch",
            validation_func=lambda r: "data" in r and isinstance(r["data"].get("branches", []), list)
        )
        
        # Test remote branches
        self.run_test(
            name="List remote branches",
            command="remote",
            validation_func=lambda r: "data" in r and isinstance(r["data"].get("remotes", []), list)
        )
        
        # Report results
        print(f"\nTest Results: {self.tests_passed}/{self.tests_run} tests passed")
        return (self.tests_passed, self.tests_run)


def interactive_mode(client: MCPGitClient):
    """
    Run the client in interactive mode
    
    Args:
        client: MCPGitClient instance
    """
    print("MCP Git Client Interactive Mode")
    print("Type 'exit' to quit")
    
    while True:
        try:
            # Get command from user
            command = input("\nCommand: ")
            if command.lower() == 'exit':
                break
                
            # Get optional parameters
            params_input = input("Parameters (JSON, press enter for none): ")
            params = {}
            if params_input.strip():
                try:
                    params = json.loads(params_input)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON parameters")
                    continue
            
            # Execute command
            response = client.send_command(command, params)
            print("\nResponse:")
            print(json.dumps(response, indent=2))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    """Main entry point for the MCP Git test client"""
    parser = argparse.ArgumentParser(description="MCP Git Server Test Client")
    parser.add_argument("--host", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=9876, help="Server port")
    parser.add_argument("--mode", choices=["interactive", "test", "command"], default="command", 
                        help="Client mode: interactive, test suite, or single command")
    parser.add_argument("command", nargs="?", help="Git command to execute (in command mode)")
    parser.add_argument("params", nargs="?", help="Command parameters as JSON (in command mode)")
    
    args = parser.parse_args()
    
    # Create client
    client = MCPGitClient(args.host, args.port)
    
    try:
        if args.mode == "interactive":
            # Run interactive mode
            interactive_mode(client)
            
        elif args.mode == "test":
            # Run test suite
            tester = MCPGitTester(client)
            tester.run_test_suite()
            
        else:  # command mode
            # Check for required command
            if not args.command:
                parser.print_help()
                sys.exit(1)
                
            # Parse parameters if provided
            params = {}
            if args.params:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON parameters")
                    sys.exit(1)
            
            # Execute command
            response = client.send_command(args.command, params)
            print(json.dumps(response, indent=2))
            
    except ConnectionRefusedError:
        print("Error: Could not connect to the server")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
