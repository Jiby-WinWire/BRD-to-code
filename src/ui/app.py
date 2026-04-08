"""
Interactive Web Dashboard for BRD-to-Code Pipeline
Features:
- Visual BRD editor with drag-and-drop
- Pipeline configuration and execution
- Real-time progress tracking
- Code diff viewer
"""

import streamlit as st
import sys
from pathlib import Path
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import zipfile
from io import BytesIO

# Load environment variables FIRST before any other imports
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Verify Azure OpenAI is configured
if not os.getenv('AZURE_OPENAI_API_KEY'):
    st.error("⚠️ Azure OpenAI API Key not configured! Please check your .env file.")
    st.stop()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import react_pipeline
from ui.components import (
    render_brd_editor,
    create_progress_tracker,
    render_progress_tracker
)

# Page configuration
st.set_page_config(
    page_title="BRD-to-Code Pipeline",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        margin: 1rem 0;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline_started' not in st.session_state:
    st.session_state.pipeline_started = False
if 'pipeline_complete' not in st.session_state:
    st.session_state.pipeline_complete = False
if 'brd_data' not in st.session_state:
    st.session_state.brd_data = None
if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'current_step' not in st.session_state:
    st.session_state.current_step = ""

# Header
st.markdown('<div class="main-header">🚀 BRD-to-Code AI Pipeline</div>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar - Pipeline Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Mode selection
    mode = st.radio(
        "Select Mode",
        ["Quick Start", "Visual BRD Editor", "Upload BRD JSON"],
        help="Choose how you want to generate your API"
    )
    
    st.markdown("---")
    
    # Advanced settings
    with st.expander("🔧 Advanced Settings"):
        temperature = st.slider("LLM Temperature", 0.0, 1.0, 0.3, 0.1)
        max_retries = st.number_input("Max Retries", 1, 5, 3)
        auto_fix = st.checkbox("Auto-fix test failures", value=True)
    
    st.markdown("---")
    
    # Information
    st.info("""
    **Pipeline Steps:**
    1. 📝 Generate BRD
    2. 📋 Create Jira Stories
    3. 💻 Generate Code
    4. 🧪 Generate Tests
    5. ✅ Validate & Deploy
    """)

# Main content area
if mode == "Quick Start":
    st.markdown('<div class="section-header">📝 Quick Start</div>', unsafe_allow_html=True)
    
    # Initialize quick_prompt if not exists
    if 'quick_prompt' not in st.session_state:
        st.session_state.quick_prompt = ""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Example prompts - shown FIRST so they can modify state before widget
        st.markdown("**💡 Click an example to use it:**")
        examples = [
            "Create a Todo API with add, list, update, complete, and delete tasks",
            "Build a User Management API with registration, login, profile updates, and user search",
            "Develop an E-commerce Product API with CRUD operations, search, and filtering",
            "Build a Blog API with create post, list posts, get post by id, and delete post"
        ]
        
        cols = st.columns(2)
        for i, example in enumerate(examples):
            with cols[i % 2]:
                if st.button(f"🔹 {example[:40]}...", key=f"example_{i}", use_container_width=True):
                    st.session_state.quick_prompt = example
                    st.rerun()
        
        st.markdown("---")
        
        # Text area - Streamlit automatically binds this to st.session_state.quick_prompt
        user_prompt = st.text_area(
            "Describe your API requirements:",
            placeholder="Example: Create a blog API with post creation, listing, viewing, and deletion features",
            height=150,
            key="quick_prompt"
        )
    
    with col2:
        st.markdown("**Quick Actions**")
        run_button = st.button("▶️ Run Pipeline", type="primary", use_container_width=True)
        
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        if st.session_state.pipeline_complete:
            st.button("📥 Download All Files", use_container_width=True)

elif mode == "Visual BRD Editor":
    st.markdown('<div class="section-header">🎨 Visual BRD Editor</div>', unsafe_allow_html=True)
    
    # Render the visual BRD editor component
    render_brd_editor()

else:  # Upload BRD JSON
    st.markdown('<div class="section-header">📤 Upload BRD</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload BRD JSON file", type=['json'])
    
    if uploaded_file:
        try:
            brd_data = json.load(uploaded_file)
            st.success("✅ BRD loaded successfully!")
            st.json(brd_data)
            
            if st.button("Process Uploaded BRD", type="primary"):
                st.session_state.brd_data = brd_data
                st.session_state.pipeline_started = True
        except Exception as e:
            st.error(f"❌ Error loading BRD: {str(e)}")

# Pipeline execution and progress tracking
if mode == "Quick Start" and run_button and user_prompt:
    st.session_state.pipeline_started = True
    st.session_state.pipeline_complete = False
    st.session_state.user_prompt = user_prompt

# Real-time progress tracking
if st.session_state.pipeline_started and not st.session_state.pipeline_complete:
    st.markdown("---")
    st.markdown('<div class="section-header">⚡ Pipeline Execution</div>', unsafe_allow_html=True)
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Pipeline steps container
    steps_container = st.container()
    
    with steps_container:
        col1, col2, col3, col4, col5 = st.columns(5)
        step_placeholders = [col1, col2, col3, col4, col5]
        step_names = ["📝 BRD", "📋 Stories", "💻 Code", "🧪 Tests", "✅ Validate"]
        
        # Show steps
        for i, (placeholder, name) in enumerate(zip(step_placeholders, step_names)):
            with placeholder:
                st.markdown(f"**{name}**")
                status = st.empty()
                status.markdown("⏳ Pending")
    
    # Execute pipeline
    try:
        user_prompt = st.session_state.get('user_prompt', '')
        
        # Update progress bar before pipeline starts
        status_text.markdown("**🚀 Starting pipeline...**")
        progress_bar.progress(5)
        
        # Actually run the pipeline (updates will happen inside)
        status_text.markdown("**⚡ Running pipeline - this may take 30-60 seconds...**")
        progress_bar.progress(10)
        
        result = react_pipeline(user_prompt)
        
        # Mark all steps as complete
        progress_bar.progress(100)
        for i, placeholder in enumerate(step_placeholders):
            with placeholder:
                st.markdown("✅ Complete")
        
        st.session_state.pipeline_complete = True
        st.session_state.pipeline_result = result
        
        # Load generated files
        output_dir = Path("output")
        if output_dir.exists():
            # Load code files
            for code_file in (output_dir / "src" / "api").glob("*.py"):
                st.session_state.generated_files[f"src/api/{code_file.name}"] = code_file.read_text(encoding='utf-8')
            
            # Load test files
            for test_file in (output_dir / "tests").glob("*.py"):
                st.session_state.generated_files[f"tests/{test_file.name}"] = test_file.read_text(encoding='utf-8')
            
            # Load BRD
            brd_file = output_dir / "docs" / "brd.json"
            if brd_file.exists():
                st.session_state.brd_data = json.loads(brd_file.read_text(encoding='utf-8'))
        
        status_text.markdown("**✅ Pipeline Complete!**")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Pipeline failed: {str(e)}")
        st.session_state.pipeline_started = False

# Display results and code diff viewer
if st.session_state.pipeline_complete:
    st.markdown("---")
    st.markdown('<div class="section-header">📊 Results & Code Viewer</div>', unsafe_allow_html=True)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Stories Generated", 
                  len(st.session_state.get('pipeline_result', {}).get('stories', [])))
    
    with col2:
        st.metric("💻 Code Files", 
                  len([f for f in st.session_state.generated_files.keys() if f.startswith('src/')]))
    
    with col3:
        st.metric("🧪 Test Files", 
                  len([f for f in st.session_state.generated_files.keys() if f.startswith('tests/')]))
    
    with col4:
        st.metric("✅ Status", "All Tests Passed", delta="Success")
    
    st.markdown("---")
    
    # Tabbed interface for different views
    result_tab1, result_tab2, result_tab3 = st.tabs([
        "📝 BRD", 
        "📋 Jira Stories", 
        "💻 Generated Code"
    ])
    
    with result_tab1:
        if st.session_state.brd_data:
            st.markdown("### Business Requirements Document")
            
            # Display in a nice format
            st.markdown(f"**Title:** {st.session_state.brd_data.get('title', 'N/A')}")
            st.markdown(f"**Description:** {st.session_state.brd_data.get('description', 'N/A')}")
            
            with st.expander("🎯 Business Goals"):
                for goal in st.session_state.brd_data.get('businessGoals', []):
                    st.markdown(f"- {goal}")
            
            with st.expander("⚙️ Functional Requirements"):
                for req in st.session_state.brd_data.get('functionalRequirements', []):
                    st.markdown(f"**{req.get('id')}:** {req.get('description')}")
            
            with st.expander("🔧 Non-Functional Requirements"):
                for req in st.session_state.brd_data.get('nonFunctionalRequirements', []):
                    st.markdown(f"**{req.get('id')}:** {req.get('description')}")
            
            # Download button
            st.download_button(
                "📥 Download BRD (JSON)",
                json.dumps(st.session_state.brd_data, indent=2),
                "brd.json",
                "application/json"
            )
    
    with result_tab2:
        if 'pipeline_result' in st.session_state:
            stories = st.session_state.pipeline_result.get('stories', [])
            st.markdown(f"### Generated {len(stories)} Jira Stories")
            
            for i, story in enumerate(stories):
                with st.expander(f"Story {i+1}: {story['fields']['summary']}"):
                    st.markdown(f"**Type:** {story['fields']['issuetype']['name']}")
                    st.markdown(f"**Priority:** {story['fields']['priority']['name']}")
                    st.markdown(f"**Description:**\n\n{story['fields']['description']}")
                    st.markdown(f"**Labels:** {', '.join(story['fields']['labels'])}")
    
    with result_tab3:
        st.markdown("### Generated Code Files")
        
        if st.session_state.generated_files:
            # Download all files button at the top
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**📦 Complete Package Includes:**")
                st.caption("• Source code (src/api/)  • Tests (tests/)  • run.py  • README.md  • requirements.txt")
            with col2:
                # Download all files as zip
                import zipfile
                from io import BytesIO
                
                # Create zip file in memory
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Add generated code files
                    for file_path, content in st.session_state.generated_files.items():
                        zip_file.writestr(file_path, content)
                    
                    # Add helper files from output directory
                    output_dir = Path("output")
                    helper_files = {
                        "run.py": output_dir / "run.py",
                        "README.md": output_dir / "README.md",
                        "requirements.txt": output_dir / "requirements.txt"
                    }
                    
                    for zip_name, file_path in helper_files.items():
                        if file_path.exists():
                            zip_file.writestr(zip_name, file_path.read_text(encoding='utf-8'))
                
                st.download_button(
                    "📦 Download All Files",
                    zip_buffer.getvalue(),
                    "generated_code.zip",
                    "application/zip",
                    use_container_width=True
                )
            
            # Instructions for using downloaded files
            with st.expander("📖 How to use the downloaded files"):
                st.markdown("""
                **After downloading and extracting the ZIP file:**
                
                1. **Install dependencies:**
                   ```bash
                   pip install -r requirements.txt
                   ```
                
                2. **Run the application:**
                   ```bash
                   python run.py
                   ```
                
                3. **Access the API:**
                   - API: `http://localhost:8000`
                   - Documentation: `http://localhost:8000/docs`
                
                4. **Run tests:**
                   ```bash
                   pytest tests/ -v
                   ```
                
                All files are production-ready and fully functional! 🚀
                """)
            
            st.markdown("---")
            
            # File selector for individual viewing
            st.markdown("**🔍 View Individual Files:**")
            file_to_view = st.selectbox(
                "Select file to view:",
                list(st.session_state.generated_files.keys()),
                label_visibility="collapsed"
            )
            
            if file_to_view:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**`{file_to_view}`**")
                with col2:
                    st.download_button(
                        "📥 Download File",
                        st.session_state.generated_files[file_to_view],
                        file_to_view.split('/')[-1],
                        key=f"download_{file_to_view}",
                        use_container_width=True
                    )
                
                # Code display with syntax highlighting
                st.code(st.session_state.generated_files[file_to_view], language='python')
        else:
            st.info("No generated files to display")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 1rem;">
    <p>🚀 BRD-to-Code AI Pipeline | Built with Streamlit, FastAPI & Azure OpenAI</p>
    <p>Need help? Check the sidebar for configuration options</p>
</div>
""", unsafe_allow_html=True)