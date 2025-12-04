
import sys
import logging
from slopspotter.vm_sandbox import deep_scan_package

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_presentation_trigger():
    print("Testing Presentation Trigger...")
    # Test with underscore version as seen in frontend
    result = deep_scan_package("demo_malware_package", "npm")
    
    if result.is_malicious and result.package_name == "demo_malware_package":
        print("\nSUCCESS: Presentation Trigger worked!")
        print(f"Confidence: {result.confidence}")
        print("Indicators:")
        for indicator in result.indicators:
            print(f" - {indicator}")
    else:
        print("\nFAILURE: Presentation Trigger did not return expected result.")
        print(result)

if __name__ == "__main__":
    test_presentation_trigger()
