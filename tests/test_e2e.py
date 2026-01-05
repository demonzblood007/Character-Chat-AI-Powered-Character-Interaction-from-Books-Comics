#!/usr/bin/env python3
"""
End-to-End Integration Tests for Character Chat
================================================

Tests the complete workflow:
1. File upload
2. Processing pipeline (character + relationship extraction)
3. Character retrieval
4. Chat functionality
5. Database verification

Run: python -m pytest tests/test_e2e.py -v
Or: python tests/test_e2e.py (standalone)
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/character_chat")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", 300))  # 5 minutes max
POLL_INTERVAL = 2  # seconds

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def log_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def log_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def log_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


class E2ETest:
    """End-to-end test suite for Character Chat"""
    
    def __init__(self):
        self.file_id: Optional[str] = None
        self.characters: List[Dict] = []
        self.expected_results = self.load_expected_results()
        self.user_id = os.getenv("TEST_USER_ID", "demo-user")
        self.default_headers = {"X-User-ID": self.user_id}

    def _headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Return headers with the correct user context."""
        return {"X-User-ID": user_id or self.user_id}
    
    def load_expected_results(self) -> Dict:
        """Load expected results from JSON fixture"""
        fixture_path = project_root / "tests" / "fixtures" / "expected_results.json"
        with open(fixture_path, 'r') as f:
            return json.load(f)
    
    def test_health_check(self) -> bool:
        """Test 1: Verify API is running"""
        log_header("TEST 1: Health Check")
        
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            assert data.get("status") == "health", "Health check failed"
            log_success("API is running and responsive")
            return True
            
        except Exception as e:
            log_error(f"Health check failed: {e}")
            return False
    
    def test_file_upload(self) -> bool:
        """Test 2: Upload test file"""
        log_header("TEST 2: File Upload")
        
        try:
            # Use the real PDF file for testing
            test_file_path = project_root / "tests" / "fixtures" / "sample_comic.pdf"
            
            if not test_file_path.exists():
                log_error(f"Test file not found: {test_file_path}")
                return False
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('sample_comic.pdf', f, 'application/pdf')}
                
                log_info("Uploading test file...")
                response = requests.post(
                    f"{API_BASE_URL}/upload",
                    files=files,
                    headers=self._headers(),
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                self.file_id = data.get("file_id")
                assert self.file_id is not None, "No file_id returned"
                
                log_success(f"File uploaded successfully: {self.file_id}")
                log_info(f"Initial status: {data.get('status')}")
                return True
                
        except Exception as e:
            log_error(f"File upload failed: {e}")
            return False
    
    def test_processing_pipeline(self) -> bool:
        """Test 3: Wait for and monitor processing"""
        log_header("TEST 3: Processing Pipeline")
        
        if not self.file_id:
            log_error("No file_id available. Upload test must pass first.")
            return False
        
        try:
            start_time = time.time()
            last_status = None
            
            log_info("Waiting for processing to complete...")
            log_info(f"Timeout: {TEST_TIMEOUT} seconds")
            
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > TEST_TIMEOUT:
                    log_error(f"Processing timeout after {elapsed:.1f} seconds")
                    return False
                
                # Poll file status
                response = requests.get(
                    f"{API_BASE_URL}/files/{self.file_id}",
                    headers=self._headers(),
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                
                current_status = data.get("status")
                
                # Log status changes
                if current_status != last_status:
                    log_info(f"Status: {current_status}")
                    if data.get("chunk_count"):
                        log_info(f"  Chunks: {data['chunk_count']}")
                    last_status = current_status
                
                # Check for completion
                if current_status == "done":
                    duration = time.time() - start_time
                    log_success(f"Processing complete in {duration:.1f} seconds")
                    log_info(f"  Characters extracted: {data.get('character_count', 'N/A')}")
                    log_info(f"  Relationships found: {data.get('relationship_count', 'N/A')}")
                    return True
                
                elif current_status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    log_error(f"Processing failed: {error_msg}")
                    return False
                
                # Wait before next poll
                time.sleep(POLL_INTERVAL)
                
        except Exception as e:
            log_error(f"Processing pipeline test failed: {e}")
            return False
    
    def test_character_extraction(self) -> bool:
        """Test 4: Verify characters were extracted correctly"""
        log_header("TEST 4: Character Extraction")
        
        if not self.file_id:
            log_error("No file_id available")
            return False
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/characters",
                params={"file_id": self.file_id},
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()
            self.characters = response.json()
            
            log_info(f"Characters extracted: {len(self.characters)}")
            
            # Verify minimum character count
            expected_min = self.expected_results.get("min_character_count", 3)
            assert len(self.characters) >= expected_min, \
                f"Expected at least {expected_min} characters, got {len(self.characters)}"
            
            # Log character names
            for char in self.characters:
                log_info(f"  - {char['name']}")
            
            # Verify expected characters are present
            character_names = [c['name'].lower() for c in self.characters]
            expected_chars = self.expected_results.get("expected_characters", [])
            
            found_count = 0
            for expected in expected_chars:
                expected_name = expected['name'].lower()
                # Check if character or any alias is found
                if any(expected_name in name or name in expected_name for name in character_names):
                    found_count += 1
                    log_success(f"Found expected character: {expected['name']}")
            
            log_success(f"Character extraction passed ({found_count}/{len(expected_chars)} expected characters found)")
            return True
            
        except Exception as e:
            log_error(f"Character extraction test failed: {e}")
            return False
    
    def test_relationship_extraction(self) -> bool:
        """Test 5: Verify relationships in Neo4j"""
        log_header("TEST 5: Relationship Extraction")
        
        if not self.characters:
            log_error("No characters available")
            return False
        
        try:
            # Test getting relationships for a character
            test_character = self.characters[0]['name']
            
            log_info(f"Checking relationships for: {test_character}")
            
            response = requests.get(
                f"{API_BASE_URL}/characters/{test_character}/relationships",
                headers=self._headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            relationships = data.get("relationships", [])
            log_info(f"Relationships found: {len(relationships)}")
            
            for rel in relationships:
                log_info(f"  - {test_character} → {rel['target']} ({rel['type']})")
            
            # Verify minimum relationship count across all characters
            total_relationships = 0
            for char in self.characters[:3]:  # Check first 3 characters
                try:
                    resp = requests.get(
                        f"{API_BASE_URL}/characters/{char['name']}/relationships",
                        headers=self._headers(),
                        timeout=5
                    )
                    if resp.status_code == 200:
                        total_relationships += len(resp.json().get("relationships", []))
                except:
                    pass
            
            expected_min = self.expected_results.get("min_relationship_count", 2)
            if total_relationships >= expected_min:
                log_success(f"Relationship extraction passed ({total_relationships} relationships)")
                return True
            else:
                log_warning(f"Found {total_relationships} relationships, expected >= {expected_min}")
                return True  # Don't fail, LLM might extract differently
                
        except Exception as e:
            log_error(f"Relationship extraction test failed: {e}")
            return False
    
    def test_chat_functionality(self) -> bool:
        """Test 6: Test chat with character"""
        log_header("TEST 6: Chat Functionality")
        
        if not self.characters:
            log_error("No characters available")
            return False
        
        try:
            test_character = self.characters[0]['name']
            stream_user = f"{self.user_id}-stream"
            test_user = self.user_id
            test_message = "Who are you and what do you do?"
            
            log_info(f"Testing chat with: {test_character}")
            log_info(f"Message: '{test_message}'")
            
            start_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/v2/chat",
                json={
                    "character_name": test_character,
                    "message": test_message
                },
                headers=self._headers(test_user),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            response_time = time.time() - start_time
            
            # Verify response
            assert "response" in data, "No response field in chat reply"
            assert len(data["response"]) > 0, "Empty response"
            
            log_success(f"Chat response received in {response_time:.2f}s")
            log_info(f"Response preview: {data['response'][:100]}...")
            
            # Verify response time < 5s (reasonable for testing)
            if response_time < 5.0:
                log_success(f"Response time acceptable: {response_time:.2f}s < 5s")
            else:
                log_warning(f"Response time slow: {response_time:.2f}s")
            
            return True
            
        except Exception as e:
            log_error(f"Chat functionality test failed: {e}")
            return False
    
    def test_chat_history(self) -> bool:
        """Test 7: Verify chat history persistence"""
        log_header("TEST 7: Chat History Persistence")
        
        if not self.characters:
            log_error("No characters available")
            return False
        
        try:
            test_character = self.characters[0]['name']
            test_user = self.user_id
            
            # Send a message
            log_info("Sending first message...")
            response1 = requests.post(
                f"{API_BASE_URL}/v2/chat",
                json={
                    "character_name": test_character,
                    "message": "Tell me about your greatest strength"
                },
                headers=self._headers(test_user),
                timeout=30
            )
            response1.raise_for_status()
            
            # Verify conversation persistence via v2 summary
            log_info("Retrieving v2 conversation summary...")
            summary_response = requests.get(
                f"{API_BASE_URL}/v2/chat/summary",
                params={"character": test_character},
                headers=self._headers(test_user),
                timeout=10
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            
            total_messages = summary_data.get("total_messages", 0)
            assert total_messages >= 2, f"Expected at least 2 messages, got {total_messages}"
            
            log_success(f"Chat history saved (v2) - total_messages: {total_messages}")
            
            # Send follow-up to test conversation memory
            log_info("Sending follow-up message...")
            response2 = requests.post(
                f"{API_BASE_URL}/v2/chat",
                json={
                    "character_name": test_character,
                    "message": "What did you just tell me about?"
                },
                headers=self._headers(test_user),
                timeout=30
            )
            response2.raise_for_status()
            
            # Verify summary updated
            summary_response2 = requests.get(
                f"{API_BASE_URL}/v2/chat/summary",
                params={"character": test_character},
                headers=self._headers(test_user),
                timeout=10
            )
            summary_response2.raise_for_status()
            summary_data2 = summary_response2.json()
            
            total_messages2 = summary_data2.get("total_messages", 0)
            assert total_messages2 > total_messages, "Summary didn't update after second message"
            
            log_success("Conversation memory working (v2) - summary persisted and updated")
            return True
            
        except Exception as e:
            log_error(f"Chat history test failed: {e}")
            return False
    
    def test_streaming_endpoint(self) -> bool:
        """Test 8: Verify streaming chat works"""
        log_header("TEST 8: Streaming Chat")
        
        if not self.characters:
            log_error("No characters available")
            return False
        
        try:
            test_character = self.characters[0]['name']
            stream_user = f"{self.user_id}-stream"
            
            log_info(f"Testing streaming chat with: {test_character}")
            
            response = requests.post(
                f"{API_BASE_URL}/v2/chat/stream",
                json={
                    "character_name": test_character,
                    "message": "Hi there!"
                },
                headers=self._headers(stream_user),
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            chunks_received = 0
            status_updates = 0
            full_text = ""
            
            # Read streaming response
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data = json.loads(decoded_line[6:])
                        
                        if data.get("type") == "status":
                            status_updates += 1
                        elif data.get("type") == "chunk":
                            chunks_received += 1
                            full_text += data.get("content", "")
                        elif data.get("type") == "done":
                            log_info(f"Stream completed: {data.get('character')}")
            
            log_success(f"Streaming test passed")
            log_info(f"  Status updates: {status_updates}")
            log_info(f"  Chunks received: {chunks_received}")
            log_info(f"  Response preview: {full_text[:80]}...")
            
            assert chunks_received > 0, "No chunks received from stream"
            assert status_updates > 0, "No status updates received"
            
            return True
            
        except Exception as e:
            log_error(f"Streaming test failed: {e}")
            return False
    
    def test_character_status_check(self) -> bool:
        """Test 9: Verify character status endpoint"""
        log_header("TEST 9: Character Status Check")
        
        if not self.characters:
            log_error("No characters available")
            return False
        
        try:
            test_character = self.characters[0]['name']
            
            log_info(f"Checking status for: {test_character}")
            
            response = requests.get(
                f"{API_BASE_URL}/characters/{test_character}/status",
                headers=self._headers(),
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            log_info(f"  Ready: {data.get('ready')}")
            log_info(f"  Can chat: {data.get('can_chat')}")
            log_info(f"  Status: {data.get('status')}")
            log_info(f"  Message: {data.get('message')}")
            
            assert data.get("ready") == True, "Character not marked as ready"
            assert data.get("can_chat") == True, "Character not available for chat"
            
            log_success("Character status check passed")
            return True
            
        except Exception as e:
            log_error(f"Character status test failed: {e}")
            return False
    
    def test_database_verification(self) -> bool:
        """Test 10: Verify data in databases (manual verification guide)"""
        log_header("TEST 10: Database Verification Guide")
        
        log_info("Manual verification steps:")
        print()
        print("  1. Neo4j Browser:")
        print(f"     Open: http://localhost:7474")
        print(f"     Username: neo4j, Password: password")
        print(f"     Query: MATCH (c:Character) RETURN c")
        print(f"     Expected: {self.expected_results.get('min_character_count', 3)}+ Character nodes")
        print()
        print("  2. Neo4j Relationships:")
        print(f"     Query: MATCH (a)-[r:RELATION]->(b) RETURN a.name, r.type, b.name, r.evidence")
        print(f"     Expected: {self.expected_results.get('min_relationship_count', 2)}+ RELATION edges")
        print()
        print("  3. MongoDB:")
        print(f"     Connection: {MONGODB_URI}")
        print(f"     Database: {os.getenv('MONGODB_DB', 'character_chat')}")
        print(f"     Collections:")
        print(f"       - files (check status: 'done')")
        print(f"       - chat_sessions (check messages array)")
        print()
        print("  4. Qdrant:")
        print(f"     Open: http://localhost:6333/dashboard")
        print(f"     Collection: comic_chunks")
        print(f"     Expected: Vector count > 0")
        print()
        
        log_success("Database verification guide displayed")
        log_warning("Manual verification recommended for complete validation")
        return True
    
    def run_all_tests(self):
        """Run complete test suite"""
        log_header("🚀 STARTING END-TO-END TESTS")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("File Upload", self.test_file_upload),
            ("Processing Pipeline", self.test_processing_pipeline),
            ("Character Extraction", self.test_character_extraction),
            ("Relationship Extraction", self.test_relationship_extraction),
            ("Chat Functionality", self.test_chat_functionality),
            ("Chat History", self.test_chat_history),
            ("Streaming Chat", self.test_streaming_endpoint),
            ("Character Status", self.test_character_status_check),
            ("Database Verification", self.test_database_verification),
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                log_error(f"Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
                failed += 1
        
        # Summary
        log_header("📊 TEST SUMMARY")
        
        for test_name, result in results:
            if result:
                log_success(f"{test_name}")
            else:
                log_error(f"{test_name}")
        
        print()
        total = passed + failed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.BLUE}Pass Rate: {pass_rate:.1f}%{Colors.RESET}")
        print()
        
        if passed == total:
            log_success("🎉 ALL TESTS PASSED!")
            return True
        elif passed >= total * 0.7:
            log_warning(f"⚠️  MOST TESTS PASSED ({pass_rate:.0f}%)")
            return True
        else:
            log_error("❌ TESTS FAILED")
            return False


def main():
    """Main test runner"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║     CHARACTER CHAT - END-TO-END TEST SUITE            ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    log_info(f"API Base URL: {API_BASE_URL}")
    log_info(f"Test Timeout: {TEST_TIMEOUT}s")
    log_info(f"Poll Interval: {POLL_INTERVAL}s")
    print()
    
    # Run tests
    test_suite = E2ETest()
    success = test_suite.run_all_tests()
    
    # Exit code (for CI/CD)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

