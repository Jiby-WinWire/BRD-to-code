#!/bin/bash
# BRD-to-Code Complete Testing Guide
# Run this script to verify installation and test both language options

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   🧪 BRD-to-Code Testing Suite                             ║"
echo "║   Language Edition: Python + C#/.NET                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ==================== COLOR DEFINITIONS ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== HELPER FUNCTIONS ====================

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ==================== SYSTEM CHECKS ====================

print_header "1. SYSTEM REQUIREMENTS CHECK"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_success "Python: $PYTHON_VERSION"
else
    print_error "Python 3 not found! Install from python.org"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 package manager found"
else
    print_error "pip3 not found!"
    exit 1
fi

# Check .NET (optional for testing)
if command -v dotnet &> /dev/null; then
    DOTNET_VERSION=$(dotnet --version)
    print_success ".NET: $DOTNET_VERSION"
else
    print_warning ".NET SDK not found - C# generation won't run, but Python will work"
fi

# ==================== DEPENDENCY CHECKS ====================

print_header "2. PYTHON DEPENDENCIES CHECK"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    print_success "Virtual environment found"
    source .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate 2>/dev/null || true
else
    print_warning "No virtual environment. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate 2>/dev/null || true
    print_success "Virtual environment created"
fi

# Check key Python packages
echo "Checking Python packages..."
python3 -c "import pydantic; print(f'  ✓ Pydantic: {pydantic.__version__}')" || print_warning "  Pydantic not found"
python3 -c "import fastapi; print(f'  ✓ FastAPI: {fastapi.__version__}')" || print_warning "  FastAPI not found"
python3 -c "import uvicorn; print(f'  ✓ Uvicorn: {uvicorn.__version__}')" || print_warning "  Uvicorn not found"

# ==================== FILE STRUCTURE CHECKS ====================

print_header "3. PROJECT FILE STRUCTURE CHECK"

files_to_check=(
    "app.py:Main entry point with language selector"
    "supervisor_language.py:Language-aware supervisor"
    "START_HERE.md:Main documentation"
    "QUICK_START.md:Quick reference guide"
    "src/agents/csharp_code_generator/__init__.py:C# code generator"
    "output/python-sample/models.py:Python sample - models"
    "output/python-sample/services.py:Python sample - services"
    "output/python-sample/main.py:Python sample - main app"
    "output/csharp-sample/Models/Todo.cs:C# sample - entity"
    "output/csharp-sample/Services/TodoService.cs:C# sample - service"
    "output/csharp-sample/Program.cs:C# sample - startup"
)

for file_info in "${files_to_check[@]}"; do
    IFS=':' read -r file description <<< "$file_info"
    if [ -f "$file" ]; then
        print_success "$description: $file"
    else
        print_error "$description: $file (NOT FOUND)"
    fi
done

# ==================== CODE SYNTAX CHECKS ====================

print_header "4. PYTHON CODE SYNTAX VALIDATION"

python_files=(
    "app.py"
    "supervisor_language.py"
    "src/agents/csharp_code_generator/__init__.py"
    "output/python-sample/models.py"
    "output/python-sample/services.py"
    "output/python-sample/main.py"
)

for file in "${python_files[@]}"; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            print_success "Syntax OK: $file"
        else
            print_error "Syntax ERROR: $file"
        fi
    fi
done

# ==================== RUNTIME TESTS ====================

print_header "5. RUNTIME TESTS"

# Test 1: Import all modules
echo "Testing Python imports..."
python3 -c "
import sys
sys.path.insert(0, '.')

try:
    from app import LanguageSelector
    print('  ✓ app.LanguageSelector imported successfully')
except Exception as e:
    print(f'  ✗ Failed to import app: {e}')

try:
    from supervisor_language import SupervisorWithLanguage
    print('  ✓ supervisor_language.SupervisorWithLanguage imported successfully')
except Exception as e:
    print(f'  ✗ Failed to import supervisor_language: {e}')

try:
    from src.agents.csharp_code_generator import CSharpCodeGenerator
    print('  ✓ CSharpCodeGenerator imported successfully')
except Exception as e:
    print(f'  ✗ Failed to import CSharpCodeGenerator: {e}')
" || print_error "Import test failed"

# ==================== PYTHON SAMPLE VALIDATION ====================

print_header "6. PYTHON SAMPLE APPLICATION VALIDATION"

echo "Validating Python sample files..."

# Check Python sample models
python3 -c "
import sys
sys.path.insert(0, 'output/python-sample')
try:
    from models import Todo, TodoCreate, TodoUpdate
    print('  ✓ All Pydantic models valid')
except Exception as e:
    print(f'  ✗ Model validation failed: {e}')
" || print_error "Python models validation failed"

# Check Python sample requirements
if [ -f "output/python-sample/requirements.txt" ]; then
    print_success "requirements.txt exists"
    echo "  Contains:"
    head -n 3 output/python-sample/requirements.txt | sed 's/^/    /'
fi

# ==================== API SPEC CHECK ====================

print_header "7. API SPECIFICATION VALIDATION"

echo "Checking API endpoint definitions..."

# Count FastAPI routes
if [ -f "output/python-sample/main.py" ]; then
    route_count=$(grep -c "@app\." output/python-sample/main.py || echo "0")
    print_success "Python FastAPI: Found $route_count route decorators"
fi

# Count ASP.NET routes
if [ -f "output/csharp-sample/Controllers/TodosController.cs" ]; then
    route_count=$(grep -c "@app\|@Http" output/csharp-sample/Controllers/TodosController.cs || echo "0")
    print_success "ASP.NET Core: Found endpoint methods"
fi

# ==================== TESTS SUMMARY ====================

print_header "📊 TEST SUMMARY"

echo "✅ Basic validation complete!"
echo ""
echo "Next steps:"
echo "  1. Run: python app.py"
echo "  2. Choose language: 1 (Python) or 2 (C#/.NET)"
echo "  3. Enter requirements"
echo "  4. Check output/[timestamp]/ folder"
echo "  5. Follow RUN_INSTRUCTIONS.txt"
echo ""
echo "Sample applications already available:"
echo "  • output/python-sample/  → python run.py"
echo "  • output/csharp-sample/  → dotnet run"
echo ""

# ==================== DETAILED TESTING INFO ====================

print_header "🔍 DETAILED TESTING OPTIONS"

echo "To manually test Python sample:"
echo "  cd output/python-sample"
echo "  pip install -r requirements.txt"
echo "  python run.py"
echo "  # Open http://localhost:8000"
echo ""

echo "To manually test C# sample:"
echo "  cd output/csharp-sample"
echo "  dotnet restore"
echo "  dotnet ef database update"
echo "  dotnet run"
echo "  # Open https://localhost:7000"
echo ""

echo "To test the language selector:"
echo "  python app.py"
echo "  # Follow the interactive prompts"
echo ""

# ==================== FINAL STATUS ====================

print_header "✨ SETUP COMPLETE"

echo "🎯 Mission Status: $(print_success 'READY FOR TESTING')"
echo ""
echo "📚 Documentation:"
echo "  • START_HERE.md      - Complete guide"
echo "  • QUICK_START.md     - Quick reference"
echo "  • Sample outputs in: output/python-sample/"
echo "                      output/csharp-sample/"
echo ""
echo "🚀 Ready to generate your first application!"
echo ""
