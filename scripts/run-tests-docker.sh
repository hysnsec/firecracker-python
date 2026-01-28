#!/bin/bash
# Script to run firecracker-python tests in Docker with KVM access

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage
print_usage() {
    echo "Usage: $0 [OPTIONS] [TEST_PATTERN]"
    echo ""
    echo "Run firecracker-python tests in Docker with KVM access"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -b, --build             Rebuild the Docker image"
    echo "  -s, --shell             Start a shell in the container instead of running tests"
    echo "  -v, --verbose           Run tests with verbose output"
    echo "  -c, --coverage          Run tests with coverage report"
    echo "  -k, --keep              Keep the container running after tests"
    echo "  -d, --detach            Run container in detached mode"
    echo ""
    echo "Arguments:"
    echo "  TEST_PATTERN             Optional test pattern to run specific tests"
    echo "                          Example: $0 test_parse_ports"
    echo ""
    echo "Examples:"
    echo "  $0                      Run all tests"
    echo "  $0 test_parse_ports     Run tests matching 'test_parse_ports'"
    echo "  $0 -v -k test_parse    Run verbose tests matching 'test_parse'"
    echo "  $0 -s                  Start a shell in the container"
    echo "  $0 -b                  Rebuild image and run all tests"
}

# Default values
BUILD=false
SHELL=false
VERBOSE=false
COVERAGE=false
KEEP=false
DETACH=false
TEST_PATTERN=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -s|--shell)
            SHELL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -k|--keep)
            KEEP=true
            shift
            ;;
        -d|--detach)
            DETACH=true
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            print_usage
            exit 1
            ;;
        *)
            TEST_PATTERN="$1"
            shift
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Check if /dev/kvm exists
if [ ! -e /dev/kvm ]; then
    echo -e "${RED}Error: /dev/kvm does not exist. KVM is not available on this system.${NC}"
    exit 1
fi

# Check if user has access to /dev/kvm
if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    echo -e "${YELLOW}Warning: User does not have read/write access to /dev/kvm${NC}"
    echo -e "${YELLOW}You may need to run: sudo chmod 666 /dev/kvm${NC}"
    echo -e "${YELLOW}Or add your user to the kvm group: sudo usermod -aG kvm \$USER${NC}"
fi

# Build the Docker image if requested
if [ "$BUILD" = true ]; then
    echo -e "${GREEN}Building Docker image...${NC}"
    docker compose -f docker-compose.test.yml build
fi

# Start the container
if [ "$SHELL" = true ]; then
    echo -e "${GREEN}Starting container with shell...${NC}"
    docker compose -f docker-compose.test.yml run --rm firecracker-test /bin/bash
else
    # Build the test command
    TEST_CMD="uv run pytest"
    
    if [ "$VERBOSE" = true ]; then
        TEST_CMD="$TEST_CMD -v"
    fi
    
    if [ "$COVERAGE" = true ]; then
        TEST_CMD="$TEST_CMD --cov=firecracker --cov-report=term-missing --cov-report=html"
    fi
    
    if [ -n "$TEST_PATTERN" ]; then
        TEST_CMD="$TEST_CMD -k $TEST_PATTERN"
    fi
    
    TEST_CMD="$TEST_CMD tests/"
    
    echo -e "${GREEN}Running tests in Docker...${NC}"
    echo -e "${YELLOW}Command: $TEST_CMD${NC}"
    echo ""
    
    if [ "$KEEP" = true ]; then
        if [ "$DETACH" = true ]; then
            echo -e "${GREEN}Starting container in detached mode...${NC}"
            docker compose -f docker-compose.test.yml up -d
            echo -e "${GREEN}Container started. Connect with: docker exec -it firecracker-python-test /bin/bash${NC}"
            echo -e "${GREEN}Run tests with: docker exec -it firecracker-python-test $TEST_CMD${NC}"
        else
            echo -e "${GREEN}Starting container and keeping it running...${NC}"
            docker compose -f docker-compose.test.yml run firecracker-test /bin/bash -c "$TEST_CMD && /bin/bash"
        fi
    else
        docker compose -f docker-compose.test.yml run --rm firecracker-test /bin/bash -c "$TEST_CMD"
    fi
fi
