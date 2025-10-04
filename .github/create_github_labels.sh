#!/bin/bash

# GitHub Labels Creation Script for Hand Controller Project
# This script creates all necessary labels for the project issues

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repository information
REPO="utnfrsn-isi-investigacion/hand-controller"

echo -e "${BLUE}🏷️ Hand Controller GitHub Labels Setup${NC}"
echo "================================================"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed.${NC}"
    echo -e "${YELLOW}Please install it: https://cli.github.com/${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub CLI.${NC}"
    echo -e "${YELLOW}Please run: gh auth login${NC}"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI is installed and authenticated${NC}"
echo ""

# Function to create a label if it doesn't exist
create_label() {
    local name="$1"
    local description="$2"
    local color="$3"
    
    # Check if label already exists
    if gh label list --repo "$REPO" | grep -q "^$name"; then
        echo -e "${YELLOW}Label '$name' already exists${NC}"
    else
        echo -e "${BLUE}Creating label: $name${NC}"
        gh label create "$name" --description "$description" --color "$color" --repo "$REPO"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Label '$name' created successfully${NC}"
        else
            echo -e "${RED}❌ Failed to create label '$name'${NC}"
        fi
    fi
}

# Create all necessary labels
echo -e "${YELLOW}🏷️ Creating GitHub Labels...${NC}"
echo ""

echo -e "${BLUE}📁 Type Labels:${NC}"
create_label "enhancement" "Improvements to existing functionality" "84b6eb"
create_label "feature" "New functionality" "0e8a16"
create_label "bug" "Something isn't working" "d73a4a"
create_label "refactoring" "Code improvement without functionality change" "fbca04"
create_label "documentation" "Documentation updates" "0075ca"
echo ""

echo -e "${BLUE}🔧 Component Labels:${NC}"
create_label "networking" "Network/TCP communication related" "1d76db"
create_label "esp32" "ESP32 microcontroller specific" "ff6b6b"
create_label "ui" "User interface changes" "bfd4f2"
create_label "visualization" "Visual feedback features" "d4c5f9"
create_label "configuration" "Configuration system related" "c2e0c6"
create_label "architecture" "System design changes" "f9c2ff"
create_label "customization" "User customization features" "c5f467"
create_label "cleanup" "Code cleanup tasks" "fef2c0"
create_label "performance" "Performance improvements" "ffa500"
echo ""

echo -e "${BLUE}🚨 Priority Labels:${NC}"
create_label "priority-high" "Must be done soon" "b60205"
create_label "priority-medium" "Should be done" "fbca04"
create_label "priority-low" "Nice to have" "0e8a16"
echo ""

echo -e "${BLUE}📋 Status Labels:${NC}"
create_label "good first issue" "Good for newcomers" "7057ff"
create_label "help wanted" "Extra attention needed" "008672"
create_label "blocked" "Cannot proceed until dependency resolved" "d93f0b"
echo ""

echo -e "${GREEN}🎉 All labels created successfully!${NC}"
echo ""

# List all labels for verification
echo -e "${BLUE}📋 Current labels in repository:${NC}"
gh label list --repo "$REPO"
echo ""

echo -e "${GREEN}✅ Setup complete! You can now run: ./create_github_issues.sh${NC}"