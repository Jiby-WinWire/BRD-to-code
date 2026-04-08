"""
Code Diff Viewer Component with Advanced Diffing
"""

import streamlit as st
import difflib
from typing import List, Tuple


def render_code_diff_viewer(generated_files: dict):
    """Render advanced code diff viewer"""
    
    st.markdown("### 📊 Code Diff Viewer")
    st.caption("Compare generated code with previous versions")
    
    # Mode selector
    diff_mode = st.radio(
        "Diff Mode",
        ["Side-by-Side", "Unified", "Line-by-Line"],
        horizontal=True
    )
    
    # File selector
    if generated_files:
        file_to_diff = st.selectbox(
            "Select file to compare:",
            list(generated_files.keys())
        )
        
        # Input methods
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Original Code** (Previous Version)")
            input_method = st.radio(
                "Input method:",
                ["Paste Code", "Upload File", "Load from Previous Run"],
                key="input_method"
            )
            
            original_code = ""
            
            if input_method == "Paste Code":
                original_code = st.text_area(
                    "Paste your original code:",
                    height=400,
                    key="original_code"
                )
            elif input_method == "Upload File":
                uploaded_file = st.file_uploader("Upload original file", type=['py'])
                if uploaded_file:
                    original_code = uploaded_file.read().decode('utf-8')
                    st.code(original_code, language='python', line_numbers=True)
            else:
                st.info("Feature coming soon: Load from previous pipeline runs")
        
        with col2:
            st.markdown("**Generated Code** (New Version)")
            new_code = generated_files.get(file_to_diff, "")
            st.code(new_code, language='python', line_numbers=True)
        
        # Show diff
        if original_code and new_code:
            st.markdown("---")
            st.markdown("### 🔍 Differences")
            
            if diff_mode == "Side-by-Side":
                render_side_by_side_diff(original_code, new_code)
            elif diff_mode == "Unified":
                render_unified_diff(original_code, new_code, file_to_diff)
            else:
                render_line_by_line_diff(original_code, new_code)
            
            # Statistics
            st.markdown("---")
            render_diff_statistics(original_code, new_code)
    else:
        st.warning("No generated files available. Run the pipeline first!")


def render_side_by_side_diff(original: str, new: str):
    """Render side-by-side diff view"""
    
    original_lines = original.split('\n')
    new_lines = new.split('\n')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Original**")
        render_colored_code(original_lines, 'original')
    
    with col2:
        st.markdown("**Generated**")
        render_colored_code(new_lines, 'new')


def render_unified_diff(original: str, new: str, filename: str):
    """Render unified diff view (like git diff)"""
    
    original_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f'original/{filename}',
        tofile=f'generated/{filename}',
        lineterm=''
    )
    
    diff_text = '\n'.join(diff)
    
    if diff_text:
        # Style the diff
        styled_diff = []
        for line in diff_text.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                styled_diff.append(f'<div style="background-color: #e6ffe6; color: #006600;">+ {line[1:]}</div>')
            elif line.startswith('-') and not line.startswith('---'):
                styled_diff.append(f'<div style="background-color: #ffe6e6; color: #660000;">- {line[1:]}</div>')
            elif line.startswith('@@'):
                styled_diff.append(f'<div style="background-color: #e6f3ff; color: #0066cc;">{line}</div>')
            else:
                styled_diff.append(f'<div style="color: #333;">{line}</div>')
        
        st.markdown(
            '<div style="font-family: monospace; font-size: 0.85rem; padding: 1rem; background-color: #f8f9fa; border-radius: 5px;">' +
            ''.join(styled_diff) +
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.success("✅ No differences found - files are identical!")


def render_line_by_line_diff(original: str, new: str):
    """Render detailed line-by-line diff"""
    
    original_lines = original.split('\n')
    new_lines = new.split('\n')
    
    # Create a differ
    differ = difflib.Differ()
    diff = list(differ.compare(original_lines, new_lines))
    
    # Group changes
    changes = []
    current_change = None
    
    for line in diff:
        if line.startswith('  '):  # Unchanged
            if current_change:
                changes.append(current_change)
                current_change = None
        elif line.startswith('- '):  # Removed
            if not current_change:
                current_change = {'type': 'change', 'original': [], 'new': []}
            current_change['original'].append(line[2:])
        elif line.startswith('+ '):  # Added
            if not current_change:
                current_change = {'type': 'change', 'original': [], 'new': []}
            current_change['new'].append(line[2:])
    
    if current_change:
        changes.append(current_change)
    
    # Display changes
    if changes:
        st.markdown(f"**Found {len(changes)} change(s)**")
        
        for i, change in enumerate(changes):
            with st.expander(f"Change {i+1}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Removed:**")
                    if change['original']:
                        for line in change['original']:
                            st.code(line, language='python')
                    else:
                        st.info("(nothing removed)")
                
                with col2:
                    st.markdown("**Added:**")
                    if change['new']:
                        for line in change['new']:
                            st.code(line, language='python')
                    else:
                        st.info("(nothing added)")
    else:
        st.success("✅ No differences found!")


def render_colored_code(lines: List[str], version: str):
    """Render code with syntax highlighting in a container"""
    code_html = []
    
    for i, line in enumerate(lines):
        code_html.append(f'<div style="padding: 2px; font-family: monospace;">'
                        f'<span style="color: #888; margin-right: 1rem;">{i+1:3d}</span>'
                        f'<span>{line}</span></div>')
    
    st.markdown(
        '<div style="background-color: #f8f9fa; padding: 1rem; border-radius: 5px; max-height: 400px; overflow-y: auto;">' +
        ''.join(code_html) +
        '</div>',
        unsafe_allow_html=True
    )


def render_diff_statistics(original: str, new: str):
    """Render statistics about the diff"""
    
    original_lines = original.split('\n')
    new_lines = new.split('\n')
    
    # Calculate statistics
    original_line_count = len(original_lines)
    new_line_count = len(new_lines)
    
    # Use difflib to get detailed statistics
    matcher = difflib.SequenceMatcher(None, original_lines, new_lines)
    
    additions = 0
    deletions = 0
    unchanged = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            unchanged += (i2 - i1)
        elif tag == 'delete':
            deletions += (i2 - i1)
        elif tag == 'insert':
            additions += (j2 - j1)
        elif tag == 'replace':
            deletions += (i2 - i1)
            additions += (j2 - j1)
    
    # Display statistics
    st.markdown("**📈 Statistics**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Lines Added", f"+{additions}", delta=None)
    
    with col2:
        st.metric("Lines Removed", f"-{deletions}", delta=None)
    
    with col3:
        st.metric("Lines Unchanged", unchanged)
    
    with col4:
        similarity = matcher.ratio() * 100
        st.metric("Similarity", f"{similarity:.1f}%")
    
    # Change summary
    if additions + deletions > 0:
        total_changes = additions + deletions
        st.progress(additions / total_changes, text=f"{additions} additions, {deletions} deletions")
