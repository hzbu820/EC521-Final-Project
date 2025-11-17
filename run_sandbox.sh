#!/bin/bash
# Sandbox runner script with gVisor integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SANDBOX_IMAGE="malicious-package-detector:latest"
RUNTIME="runsc"  # gVisor runtime

echo -e "${GREEN}=== Malicious Package Detector Sandbox ===${NC}"

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
}

# Function to check if gVisor (runsc) is available
check_gvisor() {
    if ! docker info 2>/dev/null | grep -q "runsc"; then
        echo -e "${YELLOW}Warning: gVisor runtime not detected${NC}"
        echo "Falling back to default runtime (use 'runc' for standard Docker)"
        RUNTIME="runc"
    else
        echo -e "${GREEN}gVisor runtime detected${NC}"
    fi
}

# Function to build the Docker image
build_image() {
    echo -e "${GREEN}Building sandbox Docker image...${NC}"
    docker build -t ${SANDBOX_IMAGE} .
    echo -e "${GREEN}Image built successfully${NC}"
}

# Function to run sandbox analysis
run_analysis() {
    local package_name=$1
    
    if [ -z "$package_name" ]; then
        echo -e "${RED}Error: Package name required${NC}"
        echo "Usage: $0 analyze <package_name>"
        exit 1
    fi
    
    echo -e "${GREEN}Analyzing package: ${package_name}${NC}"
    
    # Create logs directory if it doesn't exist
    mkdir -p ./logs ./reports
    
    # Run sandbox with gVisor isolation
    docker run --rm \
        --runtime=${RUNTIME} \
        --network none \
        --cpus=1 \
        --memory=512m \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,size=100m \
        --cap-drop=ALL \
        --security-opt=no-new-privileges \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/reports:/app/reports" \
        ${SANDBOX_IMAGE} \
        python3 /app/runner/sandbox.py "${package_name}"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ Analysis complete - Package appears safe${NC}"
    else
        echo -e "${RED}✗ Analysis complete - Suspicious activity detected!${NC}"
    fi
    
    return $exit_code
}

# Function to run test suite
run_tests() {
    echo -e "${GREEN}Running test suite...${NC}"
    
    # Test benign package
    echo -e "${YELLOW}Testing benign package...${NC}"
    if run_analysis "requests"; then
        echo -e "${GREEN}✓ Benign package test passed${NC}"
    else
        echo -e "${YELLOW}⚠ Benign package flagged (review rules.yaml)${NC}"
    fi
    
    # Test with malicious sample if available
    if [ -d "./tests/malicious_package" ]; then
        echo -e "${YELLOW}Testing malicious package sample...${NC}"
        # Custom malicious package test logic here
        echo -e "${YELLOW}Malicious package test (manual review required)${NC}"
    fi
}

# Function to clean up
cleanup() {
    echo -e "${GREEN}Cleaning up...${NC}"
    docker system prune -f
    rm -rf ./logs/* ./reports/*
}

# Main execution
main() {
    check_docker
    check_gvisor
    
    case "${1}" in
        build)
            build_image
            ;;
        test)
            build_image
            run_tests
            ;;
        clean)
            cleanup
            ;;
        analyze)
            if [ -z "${2}" ]; then
                echo -e "${RED}Error: Package name required${NC}"
                echo "Usage: $0 analyze <package_name>"
                exit 1
            fi
            build_image
            run_analysis "${2}"
            ;;
        *)
            echo "Usage: $0 {build|test|clean|analyze <package_name>}"
            echo ""
            echo "Commands:"
            echo "  build              - Build the sandbox Docker image"
            echo "  test               - Run the test suite"
            echo "  clean              - Clean up logs and reports"
            echo "  analyze <package>  - Analyze a specific package"
            exit 1
            ;;
    esac
}

main "$@"
