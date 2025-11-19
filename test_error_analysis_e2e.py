#!/usr/bin/env python3
"""
End-to-end test of GitHub Error Analysis Agent with Official stdio MCP Server
"""

import os
import asyncio
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.helpers.github_error_analysis_agent import analyze_error_with_github_context

load_dotenv()

async def test_error_analysis():
    print("\n" + "="*70)
    print("🧪 Testing GitHub Error Analysis Agent (End-to-End)")
    print("="*70)
    
    # Check prerequisites
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not set in .env")
        return False
    
    print(f"✅ GitHub Token: {github_token[:10]}...")
    
    # Test with a sample error
    print("\n📝 Test Scenario:")
    print("   Error: ImportError in Python file")
    print("   Repository: octocat/Hello-World (public repo)")
    print()
    
    # Create a sample error
    sample_error = None
    try:
        import requests  # This will likely fail
        # If requests is installed, create a fake ImportError
        sample_error = ImportError("No module named 'requests'")
    except ImportError as e:
        sample_error = e
    
    error_context = "Testing error analysis with GitHub context from main.py"
    
    print("⏳ Analyzing error with GitHub context...")
    print("   (This will connect to GitHub MCP server and use AI)...")
    print()
    
    try:
        result = await analyze_error_with_github_context(
            error=sample_error,
            error_context=error_context,
            session_id="test-e2e",
            company_id=1,
            origin="test",
            repository_owner="octocat",
            repository_name="Hello-World",
            file_path="README"
        )
        
        if result and "error" not in result:
            print("\n" + "="*70)
            print("✅ SUCCESS! Error Analysis Completed")
            print("="*70)
            
            print("\n📊 Analysis Result:")
            print("-" * 70)
            
            # Pretty print the result
            if isinstance(result, dict):
                for key, value in result.items():
                    if key == "analysis" and isinstance(value, str) and len(value) > 200:
                        print(f"{key}:")
                        print(f"  {value[:200]}...")
                        print(f"  ... (truncated, total {len(value)} chars)")
                    else:
                        print(f"{key}: {value}")
            else:
                print(str(result)[:500])
                if len(str(result)) > 500:
                    print("... (truncated)")
            
            print("\n" + "="*70)
            print("🎉 End-to-End Test PASSED!")
            print("="*70)
            print("\n✅ The GitHub Error Analysis Agent is working with:")
            print("   - Official GitHub MCP Server (stdio)")
            print("   - Google ADK/Gemini AI")
            print("   - GitHub API via MCP tools")
            print()
            
            return True
        else:
            print(f"\n❌ Analysis failed: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_error_analysis())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

